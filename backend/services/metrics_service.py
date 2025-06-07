from typing import Dict, List, Optional
from datetime import datetime, timedelta
from backend.db.database import DatabaseConnection
import pandas as pd
import numpy as np

class MetricsService:
    def __init__(self):
        self.db = DatabaseConnection()

    async def get_performance_metrics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get model performance metrics"""
        query = """
        WITH feedback_metrics AS (
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as total_predictions,
                AVG(CASE WHEN feedback_type = 'correct' THEN 1 ELSE 0 END) as accuracy,
                AVG(confidence) as avg_confidence
            FROM model_feedback
            WHERE created_at BETWEEN %(start_date)s AND %(end_date)s
            GROUP BY DATE(created_at)
        )
        SELECT 
            date,
            total_predictions,
            ROUND(accuracy * 100, 2) as accuracy_percentage,
            ROUND(avg_confidence * 100, 2) as confidence_percentage
        FROM feedback_metrics
        ORDER BY date
        """
        try:
            results = await self.db.execute_query(query, {
                'start_date': start_date,
                'end_date': end_date
            })
            
            # Calculate overall metrics
            if results:
                df = pd.DataFrame(results)
                overall_metrics = {
                    'average_accuracy': df['accuracy_percentage'].mean(),
                    'average_confidence': df['confidence_percentage'].mean(),
                    'total_predictions': df['total_predictions'].sum(),
                    'trend': self._calculate_trend(df['accuracy_percentage'])
                }
            else:
                overall_metrics = {
                    'average_accuracy': 0,
                    'average_confidence': 0,
                    'total_predictions': 0,
                    'trend': 'stable'
                }
            
            return {
                'daily_metrics': results,
                'overall_metrics': overall_metrics
            }
        except Exception as e:
            raise Exception(f"Error retrieving performance metrics: {str(e)}")

    async def get_confidence_metrics(self) -> Dict:
        """Get model confidence distribution"""
        query = """
        WITH confidence_buckets AS (
            SELECT 
                CASE 
                    WHEN confidence >= 0.9 THEN 'very_high'
                    WHEN confidence >= 0.7 THEN 'high'
                    WHEN confidence >= 0.5 THEN 'medium'
                    ELSE 'low'
                END as confidence_level,
                COUNT(*) as count,
                AVG(CASE WHEN feedback_type = 'correct' THEN 1 ELSE 0 END) as accuracy
            FROM model_feedback
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY confidence_level
        )
        SELECT 
            confidence_level,
            count,
            ROUND(accuracy * 100, 2) as accuracy_percentage
        FROM confidence_buckets
        ORDER BY confidence_level
        """
        try:
            results = await self.db.execute_query(query)
            return {
                'distribution': results,
                'summary': self._calculate_confidence_summary(results)
            }
        except Exception as e:
            raise Exception(f"Error retrieving confidence metrics: {str(e)}")

    async def get_error_analysis(self) -> Dict:
        """Get error analysis metrics"""
        query = """
        SELECT 
            test_name,
            COUNT(*) as total_predictions,
            AVG(CASE WHEN feedback_type = 'incorrect' THEN 1 ELSE 0 END) as error_rate,
            AVG(confidence) as avg_confidence
        FROM model_feedback
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            AND feedback_type = 'incorrect'
        GROUP BY test_name
        HAVING COUNT(*) >= 5
        ORDER BY error_rate DESC
        LIMIT 10
        """
        try:
            results = await self.db.execute_query(query)
            return {
                'top_errors': results,
                'error_patterns': await self._analyze_error_patterns()
            }
        except Exception as e:
            raise Exception(f"Error retrieving error analysis: {str(e)}")

    async def get_usage_stats(self, period: str = 'daily') -> Dict:
        """Get API usage statistics"""
        period_clause = {
            'daily': "DATE(created_at)",
            'weekly': "DATE_TRUNC('week', created_at)",
            'monthly': "DATE_TRUNC('month', created_at)"
        }.get(period, "DATE(created_at)")
        
        query = f"""
        SELECT 
            {period_clause} as period,
            COUNT(*) as total_requests,
            COUNT(DISTINCT test_name) as unique_tests,
            AVG(EXTRACT(EPOCH FROM response_time)) as avg_response_time
        FROM api_logs
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY period
        ORDER BY period
        """
        try:
            results = await self.db.execute_query(query)
            return {
                'usage_metrics': results,
                'summary': self._calculate_usage_summary(results)
            }
        except Exception as e:
            raise Exception(f"Error retrieving usage statistics: {str(e)}")

    def _calculate_trend(self, series: pd.Series) -> str:
        """Calculate trend direction based on recent data"""
        if len(series) < 2:
            return 'stable'
        
        slope = np.polyfit(range(len(series)), series, 1)[0]
        if slope > 0.5:
            return 'improving'
        elif slope < -0.5:
            return 'declining'
        return 'stable'

    def _calculate_confidence_summary(self, results: List[Dict]) -> Dict:
        """Calculate summary statistics for confidence distribution"""
        if not results:
            return {}
            
        total = sum(r['count'] for r in results)
        return {
            'high_confidence_ratio': sum(r['count'] for r in results 
                                      if r['confidence_level'] in ['very_high', 'high']) / total,
            'average_accuracy': sum(r['accuracy_percentage'] * r['count'] for r in results) / total
        }

    async def _analyze_error_patterns(self) -> Dict:
        """Analyze patterns in model errors"""
        query = """
        SELECT 
            feedback_type,
            confidence_level,
            COUNT(*) as count
        FROM (
            SELECT 
                feedback_type,
                CASE 
                    WHEN confidence >= 0.9 THEN 'very_high'
                    WHEN confidence >= 0.7 THEN 'high'
                    WHEN confidence >= 0.5 THEN 'medium'
                    ELSE 'low'
                END as confidence_level
            FROM model_feedback
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
        ) subquery
        GROUP BY feedback_type, confidence_level
        """
        try:
            results = await self.db.execute_query(query)
            return self._process_error_patterns(results)
        except Exception as e:
            raise Exception(f"Error analyzing error patterns: {str(e)}")

    def _calculate_usage_summary(self, results: List[Dict]) -> Dict:
        """Calculate summary statistics for API usage"""
        if not results:
            return {}
            
        return {
            'total_requests': sum(r['total_requests'] for r in results),
            'avg_response_time': sum(r['avg_response_time'] for r in results) / len(results),
            'peak_requests': max(r['total_requests'] for r in results)
        }