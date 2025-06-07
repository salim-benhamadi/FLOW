from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import pandas as pd

class PlotDialog(QDialog):
    def __init__(self, input_data, reference_data, test_name, parent=None):
        super().__init__(parent)
        self.input_data = pd.to_numeric(np.array(input_data), errors='coerce')
        self.reference_data = pd.to_numeric(np.array(reference_data), errors='coerce')
        self.test_name = test_name
        self.current_plot = 'kde'
        
        try:
            if parent and hasattr(parent, 'data'):
                df = parent.data
                row = df[df['Test Name'] == test_name].iloc[0]
                self.lsl_input = row.get('LSL_input')
                self.usl_input = row.get('USL_input')
                self.lsl_ref = row.get('LSL_reference')
                self.usl_ref = row.get('USL_reference')
            else:
                self.lsl_input = self.usl_input = self.lsl_ref = self.usl_ref = None
        except Exception as e:
            print(f"Error getting limits: {str(e)}")
            self.lsl_input = self.usl_input = self.lsl_ref = self.usl_ref = None
            
        self.initUI()

    def get_plot_range(self, data1, data2, limits):
        all_data = np.concatenate([data1, data2])
        data_range = np.percentile(all_data, [1, 99])
        margin = (data_range[1] - data_range[0]) * 0.1
        
        min_limit = min(limit for limit in limits if limit is not None and not np.isnan(limit)) if limits else None
        max_limit = max(limit for limit in limits if limit is not None and not np.isnan(limit)) if limits else None
        
        plot_min = min(data_range[0] - margin, min_limit) if min_limit is not None else data_range[0] - margin
        plot_max = max(data_range[1] + margin, max_limit) if max_limit is not None else data_range[1] + margin
        
        return plot_min, plot_max
        
    def initUI(self):
        plt.style.use('default')
        sns.set_style("whitegrid")
        
        self.setWindowTitle(f"Distribution Plot - {self.test_name}")
        self.setMinimumSize(1000, 600)
        
        layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        plot_types = ["KDE", "Histogram", "Box Plot", "Cumulative Frequency"]
        self.buttons = {}
        
        for plot_type in plot_types:
            btn = QPushButton(plot_type)
            btn.setMinimumWidth(150)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 2px solid #c0c0c0;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)
            plot_type_key = plot_type.lower().replace(" ", "_")
            btn.clicked.connect(lambda checked, pt=plot_type_key: self.update_plot(pt))
            button_layout.addWidget(btn)
            self.buttons[plot_type_key] = btn
            
        layout.addLayout(button_layout)
        
        self.fig = Figure(figsize=(12, 7), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
        
        self.update_plot("kde")

    def plot_limits(self, ax, plot_type="default"):
        limit_lines = []
        limit_labels = []
        
        if plot_type == "box_plot":
            if self.lsl_input is not None and not np.isnan(self.lsl_input):
                line = ax.axhline(y=self.lsl_input, color='blue', linestyle='--', alpha=0.7)
                limit_lines.append(line)
                limit_labels.append('LSL Input')
                
            if self.usl_input is not None and not np.isnan(self.usl_input):
                line = ax.axhline(y=self.usl_input, color='blue', linestyle='--', alpha=0.7)
                limit_lines.append(line)
                limit_labels.append('USL Input')
                
            if self.lsl_ref is not None and not np.isnan(self.lsl_ref):
                line = ax.axhline(y=self.lsl_ref, color='red', linestyle='--', alpha=0.7)
                limit_lines.append(line)
                limit_labels.append('LSL Reference')
                
            if self.usl_ref is not None and not np.isnan(self.usl_ref):
                line = ax.axhline(y=self.usl_ref, color='red', linestyle='--', alpha=0.7)
                limit_lines.append(line)
                limit_labels.append('USL Reference')
        else:            
            if self.lsl_input is not None and not np.isnan(self.lsl_input):
                line = ax.axvline(x=self.lsl_input, color='blue', linestyle='--', alpha=0.7)
                limit_lines.append(line)
                limit_labels.append('LSL Input')
                
            if self.usl_input is not None and not np.isnan(self.usl_input):
                line = ax.axvline(x=self.usl_input, color='blue', linestyle='--', alpha=0.7)
                limit_lines.append(line)
                limit_labels.append('USL Input')
                
            if self.lsl_ref is not None and not np.isnan(self.lsl_ref):
                line = ax.axvline(x=self.lsl_ref, color='red', linestyle='--', alpha=0.7)
                limit_lines.append(line)
                limit_labels.append('LSL Reference')
                
            if self.usl_ref is not None and not np.isnan(self.usl_ref):
                line = ax.axvline(x=self.usl_ref, color='red', linestyle='--', alpha=0.7)
                limit_lines.append(line)
                limit_labels.append('USL Reference')
            
        return limit_lines, limit_labels

    def update_plot(self, plot_type):
        try:
            self.fig.clear()
            plt.style.use('default')
            sns.set_style("whitegrid")
            
            ax = self.fig.add_subplot(111)
            self.fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.1)
            
            input_data = self.input_data[~np.isnan(self.input_data) & ~np.isinf(self.input_data)]
            reference_data = self.reference_data[~np.isnan(self.reference_data) & ~np.isinf(self.reference_data)]
            
            if plot_type == "kde":
                if len(input_data) < 2 or len(reference_data) < 2:
                    ax.text(0.5, 0.5, 'Not enough valid data points for KDE plot',
                           ha='center', va='center', transform=ax.transAxes)
                else:
                    limits = [self.lsl_input, self.usl_input, self.lsl_ref, self.usl_ref]
                    plot_min, plot_max = self.get_plot_range(input_data, reference_data, limits)
                    
                    sns.kdeplot(data=input_data, ax=ax, label='Input Data',
                              color='#1f77b4', fill=True, alpha=0.3,
                              common_norm=False, bw_adjust=1.5,
                              cut=3)
                    
                    sns.kdeplot(data=reference_data, ax=ax, label='Reference Data',
                              color='#ff7f0e', fill=True, alpha=0.3,
                              common_norm=False, bw_adjust=1.5,
                              cut=3)
                    
                    ax.set_xlim(plot_min, plot_max)
                
                ax.set_ylabel("Density")
                
            elif plot_type == "histogram":
                bins = min(int(np.sqrt(len(input_data))), 50)
                
                sns.histplot(data=input_data, ax=ax, label='Input Data', 
                        color='#1f77b4', alpha=0.5, stat='density', 
                        kde=True, bins=bins)
                sns.histplot(data=reference_data, ax=ax, label='Reference Data', 
                        color='#ff7f0e', alpha=0.5, stat='density', 
                        kde=True, bins=bins)
                ax.set_ylabel("Density")
                
            elif plot_type == "box_plot":
                plot_data = pd.DataFrame({
                    'Input Data': input_data,
                    'Reference Data': reference_data
                })
                
                sns.boxplot(data=plot_data, ax=ax, palette=['#1f77b4', '#ff7f0e'])
                ax.set_ylabel("Value")
                
            elif plot_type == "cumulative_frequency":
                self.create_cumulative_frequency_plot(ax, input_data, '#1f77b4', 'Input Data')
                self.create_cumulative_frequency_plot(ax, reference_data, '#ff7f0e', 'Reference Data')
                
                prob_points = [0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 0.999]
                ax.set_yticks(stats.norm.ppf(prob_points))
                ax.set_yticklabels([f'{p*100:.1f}%' for p in prob_points])
                ax.set_ylabel("Cumulative Probability")

            limit_lines, limit_labels = self.plot_limits(ax, plot_type)
            
            handles, labels = ax.get_legend_handles_labels()
            handles.extend(limit_lines)
            labels.extend(limit_labels)
            
            if plot_type != "box_plot":
                for loc in ['best', 'upper right', 'upper left', 'lower right', 'lower left']:
                    try:
                        legend = ax.legend(handles, labels, loc=loc, frameon=True, 
                                        fancybox=True, framealpha=0.9)
                        if legend:
                            break
                    except:
                        continue
            
            ax.set_title(f"{plot_type.replace('_', ' ').title()} - {self.test_name}", pad=20)
            ax.set_xlabel("Value")
            ax.grid(True, linestyle='--', alpha=0.7)
            
            self.fig.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating plot: {str(e)}")
            import traceback
            traceback.print_exc()

    def create_cumulative_frequency_plot(self, ax, data, color, label):
        try:
            data_array = np.array(data)
            valid_data = data_array[~np.isnan(data_array)]
            
            if len(valid_data) == 0:
                print(f"No valid data for {label}")
                return ax
                
            sorted_data = np.sort(valid_data)
            n_valid = len(sorted_data)
            
            emp_prob = (np.arange(1, n_valid + 1) - 0.5) / n_valid
            y = stats.norm.ppf(emp_prob)
            
            q1x, q3x = np.percentile(sorted_data, [25, 75])
            q1y, q3y = np.percentile(y, [25, 75])

            ax.plot([q1x, q3x], [q1y, q3y], color='gray', linewidth=2)
            ax.plot(sorted_data, y, 'o', color=color, label=label, markersize=4, alpha=0.6)
            
        except Exception as e:
            print(f"Error creating cumulative frequency plot: {str(e)}")
            
        return ax

    def closeEvent(self, event):
        plt.close(self.fig)
        super().closeEvent(event)