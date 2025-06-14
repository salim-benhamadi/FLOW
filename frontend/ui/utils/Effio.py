import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
import os
import re
import csv
HEADER_END_STRING = "<+EFF:1.00>"
TEST_NUMBERS_COLS = ["<+ParameterNumber>", "<+PNumber>", "<+ParameterName>", "<+EFF:1.00>"]
LSL_COLUMNS = ["<lsl>", "<limit:spec:lower_value>"]
USL_COLUMNS = ["<usl>", "<limit:spec:upper_value>"]
ENCODING_LIST = ['utf-8', 'ISO-8859-1']
HEADER_START_STRING = "<<EFF:1.00>>"
HEADER_END_STRING = "<+EFF:1.00>"
CONVERSION_FACTORS = {'m': 1e-3, 'u': 1e-6, 'n': 1e-9, 'k': 1e3, 'M': 1e6, 'G': 1e9}
UNIT_MAPPING = {'Sec': 's', 'hz': 'Hz', 'ohm': 'Ohm', 'v': 'V'}
UNITS_LIST = ["Unit", "unit", "Units", "units", "<Unit>"]
ROWS_TO_SKIP = ["Skew", "Cp", "Cpk", "Yield"]

def convert(data , inplace  = False):
    """
    Convert the units of measurement in the input DataFrame to the standard SI units.

    Args:
        df (pandas.DataFrame): The input DataFrame containing the data to be converted.

    Returns:
        pandas.DataFrame: The modified DataFrame with units converted to SI units.

    Note: This function modifies the input DataFrame in-place. If you need to preserve the original DataFrame, make a copy before calling this function.
    """

    def convert_unit_to_SI(unit):
        if unit and unit[0] in CONVERSION_FACTORS:
            return unit[1:]  
        else:
            return unit

    def convert_nonStandard_units(unit):
        return UNIT_MAPPING.get(unit, unit)  

    def convert_measured_values(value, unit):
        try:
            numeric_value = float(value)
            if unit and unit[0] in CONVERSION_FACTORS:
                return numeric_value * CONVERSION_FACTORS[unit[0]]
            else:
                return numeric_value
        except ValueError:
            return value  
    
    df = data if inplace else data.copy()
    rows_to_skip_indices = []
    for index, row in df.iterrows():
        if any(word in str(row.iloc[0]) for word in ROWS_TO_SKIP):
            rows_to_skip_indices.append(index)
    unit_row_index = None
    for index, row in df.iterrows():
        non_empty_columns = row.dropna().index
        if len(non_empty_columns) > 0:
            for word in UNITS_LIST:
                if word in row[non_empty_columns[0]]:
                    unit_row_index = index
                    break
            if unit_row_index is not None:
                break
    if unit_row_index is not None:
        for column in df.columns[1:]:
            if pd.notnull(df.at[unit_row_index, column]):
                unit = df.at[unit_row_index, column]
                converted_unit = convert_unit_to_SI(unit)
                df.at[unit_row_index, column] = converted_unit

                for i in range(len(df)):
                    if i != unit_row_index and i not in rows_to_skip_indices:
                        original_value = df.at[i, column]
                        converted_value = convert_measured_values(original_value, unit)
                        df.at[i, column] = converted_value

        for column in df.columns:
            if column != df.columns[0] and pd.notnull(df.at[unit_row_index, column]):
                unit = df.at[unit_row_index, column]
                Standard_unit = convert_nonStandard_units(unit)
                df.at[unit_row_index, column] = Standard_unit

    return df


    
def get_description_rows(df, header = None): # Robust # Verified
    """
    Extracts description rows from Eff file.

    Parameters:
        df: pandas.DataFrame
            Input pandas DataFrame from which description rows data is extracted.
        header: str, optional
            If a specific row label is provided, that row will be used as column headers.
            If None, the header will be inferred from the input DataFrame.
            If 'auto', the row containing the test numbers will be used as column headers. 

    Returns:
        pandas.DataFrame
            A DataFrame that only includes the description rows.

    Raises: 
        TypeError
            If the input is not a pandas DataFrame.
        ValueError
            If the input DataFrame does not contain any description rows.

    Examples: 
        >>> df, metadata = EFF.read('path/to/file.eff')
        >>> EFF.get_description_rows(df)
            <+EFF:1.00>  Lot    Split  Wafer X     Y     VNr  Date      Device   Process YIO5A:XLoc YIO5A:YLoc YIO5A:XSize YIO5A:YSize YBS3:Yield  
            <DataType>   Text   Text   Text  Int   Int   Text Date       Text     Text    Int        Int        Int         Int         Double     
            <ColType>    K      K      K     K     K     K    N          N        N       V          V          V           V           V          
            <Unit>                                                                                                                      %          
            
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError('Input must be a pandas DataFrame.')

    # Identify the row index where header data ends.
    header_end_index = get_values_rows_index(df)
    

    # Return only the rows that contain header data.
    header_rows = df.iloc[:header_end_index - 1,:]

    if header is not None:
        if header == "auto":
            header_rows.columns = get_test_numbers_row(df)
        else: 
            try:
                header_rows.columns = get_row(df, header)
            except KeyError:
                print(f"Error: Header '{header}' not found in the input DataFrame.")

    if header_rows.empty:
        raise ValueError('The input DataFrame does not contain any header rows.')

    return header_rows

def get_test_numbers_row(df):  # Robust # Verified
    """
    Extracts the raw that contains test numbers from a DataFrame.

    Parameters:
        df: pandas.DataFrame
            Input pandas DataFrame from which test numbers are extracted.

    Returns:
        list
            A list of test numbers extracted from the input DataFrame.

    Notes:
        The method searches for specific columns related to parameter numbers and extracts the corresponding values.
        If the specified columns are not found, it returns the column names of the input DataFrame.

    Example:
        >>> df, metadata = EFF.read('path/to/file.eff')
        >>> result = get_test_numbers_row(df)
        >>> result 
        <+ParameterNumber>    343      2423     23423     2342   
    """
    for row in TEST_NUMBERS_COLS:
        if row in df.index:
            test_numbers = [c for c in df.loc[row] if str(c).isdigit()]
            if test_numbers:
                return df.loc[row].values
    return df.columns

def correct_types(df):
    """
    Correct the data types in each column to match the inferred data types from the DataFrame.

    Args:
        df (pandas.DataFrame): The DataFrame to be corrected.

    Returns:
        pandas.DataFrame: The corrected DataFrame with data types matching the inferred types.

    Examples: 
        >>> data = pd.DataFrame({'A': ['1', '2', '3'],
        ...                       'B': ['2022-01-01', '2022-01-02', '2022-01-03'],
        ...                       'C': ['a', 'b', 'c']})
        >>> correct_types(data)
            A          B    C
        0    1 2022-01-01    a
        1    2 2022-01-02    b
        2    3 2022-01-03    c
    """
    def parse(x):
        try:
            if pd.api.types.is_datetime64_any_dtype(x):
                return pd.to_datetime(x)
            else:
                return pd.to_numeric(x)
        except:
            return x
    df_corrected = df.apply(lambda x: parse(x))

    return df_corrected

def get_values_rows_index(df): # Robust # Verified
        """
        Extracts the index of the row in a DataFrame where the measurement data start.

        Parameters:
            df: pandas.DataFrame
                Input pandas DataFrame from which measurement data is extracted.

        Returns:
            int
                The index of the row where the measurement data start.

        Raises:
            TypeError
                If the input is not a pandas DataFrame.

        Examples: 
            >>> df, metadata = read('path/to/file.eff')
            >>> EFF.get_values_rows_index(df)
            2
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError('Input must be a pandas DataFrame.')

        # Identify the row index where measurement data starts.
        # This is assumed to be after the last row that contains '<' in the first column.
        data_index = len([entry for entry in df.index if '<' in str(entry)])

        return data_index

def get_row(df, rowname):  # Robust # Verified
    """
    Retrieve a specific row from a DataFrame based on a given row name.

    Parameters:
        df (pd.DataFrame): DataFrame containing the data.
        rowname (str): Name of the row to be retrieved.

    Returns:
        pd.DataFrame: A DataFrame containing the specific row data.

    Raises:
        ValueError: If the HEADER_END_STRING is not found in the DataFrame.
        KeyError: If the row name is not found in the DataFrame.

    Example:
        >>> specific_row = EFF.get_row(data_frame, '<DataType>')
        <DataType>   Text   Text   Text  Int   Int   Text Date       Text     Text    Int        Int        Int         Int         Double     
    """
    try:
        specific_row = df.loc[df.index.str.lower() == rowname.lower()]
        if specific_row.empty:
            raise KeyError(f"The row with name '{rowname}' does not exist in the DataFrame.")
        return specific_row.values[0]
    except KeyError as ke:
        raise ke
    except Exception as e:
        raise ValueError(f"An error occurred while retrieving the row: {e}")
    
class EFF:
    @staticmethod
    def read(filepath, si=False): 
        """
        Reads data from an EFF file and processes it into a pandas DataFrame.

        Args:
            filepath (str): The path to the EFF file to be read.
            si (bool, optional): Whether to convert to international system units. Defaults to False.

        Returns:
            A tuple containing the DataFrame and the metadata.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            Exception: If there is an issue with decoding the file.

        Example:
            >>> df, metadata = EFF.read('path/to/file.eff')
            >>> print(df.head())
                <+EFF:1.00>  Lot    Split  Wafer X     Y     VNr  Date      Device   Process YIO5A:XLoc YIO5A:YLoc YIO5A:XSize YIO5A:YSize YBS3:Yield  
                <DataType>   Text   Text   Text  Int   Int   Text Date       Text     Text    Int        Int        Int         Int         Double     
                <ColType>    K      K      K     K     K     K    N          N        N       V          V          V           V           V          
                <Unit>                                                                                                                      %          
                20_Lot       A53789 .01                           2000-03-28 256M_D17 PLY                                                   5.791E+01  
                15_Waf       A53789 .01    12                     2000-03-28 256M_D17 PLY                                                   3.875E+01  
                05_Die       A53789 .01    12    22    10    01   2000-03-28 256M_D17 PLY     855372     758473     123         399                    
                05_Die       A53789 .01    12    22    10    02   2000-03-28 256M_D17 PLY     322456     150023     567         201                    
                05_Die       A53789 .01    12    22    10    03   2000-03-28 256M_D17 PLY     145567     988344     12          321                    
                05_Die       A53789 .01    12    22    10    04   2000-03-28 256M_D17 PLY     277800     467890     722         599                    
                05_Die       A53789 .01    12    7     5     01   2000-03-28 256M_D17 PLY     644124     800320     489         965                    
                05_Die       A53789 .01    12    7     5     02   2000-03-28 256M_D17 PLY     199541     288133     117         722                    
                15_Waf       A53789 .01    15                     2000-03-28 256M_D17 PLY                                                   7.923E+01  
                05_Die       A53789 .01    15    12    17    01   2000-03-28 256M_D17 PLY     557102     888456     788         229                    
                05_Die       A53789 .01    15    12    17    02   2000-03-28 256M_D17 PLY     236612     567833     603         892                    
                05_Die       A53789 .01    15    12    17    03   2000-03-28 256M_D17 PLY     778340     228990     337         442                    
                05_Die       A53789 .01    15    18    41    01   2000-03-28 256M_D17 PLY     130888     678229     589         900                    

            >>> print(metadata)
                [<<EFF:1.00>>  Headers=2  Rows=18  Columns=15  JobId=2000121912332412:P01  
                <<History>>  EXT_DDE V2.9 (2001-04-04 12:33:22)]
        """

        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"File '{filepath}' does not exist")
        
        for encoding in ENCODING_LIST:
            try:
                with open(filepath, 'r', encoding=encoding) as file:
                    reader = csv.reader(file, delimiter=';')
                    rows = list(reader)
                    header_rows_count = 0
                    for hrow in rows:
                        if "<+" in hrow[0]: break
                        header_rows_count += 1
                    data_rows = rows[header_rows_count:]
                    metadata = rows[:header_rows_count]
                    length_r0, length_r1 = len(data_rows[0]), len(data_rows[1])
                    if length_r1 > length_r0:
                        data_rows[0].extend(['no test number assigned'] * (length_r1 - length_r0))
                    df = pd.DataFrame(data_rows[1:], columns=data_rows[0])
                    df.set_index(df.columns[0], inplace=True)
                return (df, metadata) if not si else (convert(df), metadata)
            except UnicodeDecodeError:
                pass
    
    @staticmethod
    def lsl(df: pd.DataFrame, test_numbers: list[str]) -> list[float]:
        """
        Get the Lower Specification Limit (LSL) values for specific tests from the dataframe.

        Args:
            df (pd.DataFrame): The input dataframe containing the test data.
            test_numbers (list[str]): List of the numbers of the tests for which LSL is to be retrieved.

        Returns:
            list[float]: The LSL values for the specified tests. Returns np.nan if the value is null.

        Raises:
            ValueError: If the LSL columns are not found in the dataframe.

        Example:
            >>> lsl_values = EFF.lsl(df, ["50030", "39949","39349","39249"])
            >>> print(lsl_values)
            [10.0, 15.0, nan, nan]
        """
        data = get_description_rows(df, header="auto")

        lsl_columns = [col for col in data.index if col.lower() in LSL_COLUMNS]
        if not lsl_columns:
            raise ValueError(f"Lower Specification Limit (LSL) not found in DataFrame.")

        lsl_values = data.loc[lsl_columns[0], test_numbers].values.flatten()
        return [pd.to_numeric(val) for val in lsl_values]

    @staticmethod
    def usl(df: pd.DataFrame, test_numbers: list[str]) -> list[float]:
        """
        Get the Upper Specification Limit (USL) values for specific tests from the dataframe.

        Args:
            df (pd.DataFrame): The input dataframe containing the test data.
            test_numbers (list[str]): List of the numbers of the tests for which USL is to be retrieved.

        Returns:
            list[float]: The USL values for the specified tests. Returns np.nan if the value is null.

        Raises:
            ValueError: If the USL columns are not found in the dataframe.
        
        Example:
            >>> usl_values = EFF.usl(df, ["50030", "39949","39349","39249"])
            >>> print(usl_values)
            [9.0, 13.0, nan, nan]
        """
        data = get_description_rows(df, header="auto")

        usl_columns = [col for col in data.index if col.lower() in USL_COLUMNS]
        if not usl_columns:
            raise ValueError(f"Upper Specification Limit (USL) not found in DataFrame.")

        usl_values = data.loc[usl_columns[0], test_numbers].values.flatten()
        return [pd.to_numeric(val) for val in usl_values]

    @staticmethod
    def get_description_rows(df, header = None): # Robust # Verified
        """
        Extracts description rows from Eff file.

        Parameters:
            df: pandas.DataFrame
                Input pandas DataFrame from which description rows data is extracted.
            header: str, optional
                If a specific row label is provided, that row will be used as column headers.
                If None, the header will be inferred from the input DataFrame.
                If 'auto', the row containing the test numbers will be used as column headers. 

        Returns:
            pandas.DataFrame
                A DataFrame that only includes the description rows.

        Raises: 
            TypeError
                If the input is not a pandas DataFrame.
            ValueError
                If the input DataFrame does not contain any description rows.

        Examples: 
            >>> df, metadata = EFF.read('path/to/file.eff')
            >>> EFF.get_description_rows(df)
                <+EFF:1.00>  Lot    Split  Wafer X     Y     VNr  Date      Device   Process YIO5A:XLoc YIO5A:YLoc YIO5A:XSize YIO5A:YSize YBS3:Yield  
                <DataType>   Text   Text   Text  Int   Int   Text Date       Text     Text    Int        Int        Int         Int         Double     
                <ColType>    K      K      K     K     K     K    N          N        N       V          V          V           V           V          
                <Unit>                                                                                                                      %          
                
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError('Input must be a pandas DataFrame.')

        # Identify the row index where header data ends.
        header_end_index = get_values_rows_index(df)
        

        # Return only the rows that contain header data.
        header_rows = df.iloc[:header_end_index - 1,:]

        if header is not None:
            if header == "auto":
                header_rows.columns = get_test_numbers_row(df)
            else: 
                try:
                    header_rows.columns = get_row(df, header)
                except KeyError:
                    print(f"Error: Header '{header}' not found in the input DataFrame.")

        if header_rows.empty:
            raise ValueError('The input DataFrame does not contain any header rows.')

        return header_rows
    @staticmethod
    def parse_eff_headers(eff_file: str) -> Dict[str, List[str]]:
        headers = {}
        
        try:
            with open(eff_file, 'r', encoding='utf-8') as file:
                for line in file:
                    if not line.startswith('<'):
                        break
                    
                    parts = line.strip().split(';')
                    if len(parts) > 0:
                        tag = parts[0]
                        values = [val.strip() for val in parts[1:]]
                        headers[tag] = values
                        
        except Exception as e:
            print(f"Error parsing EFF headers: {str(e)}")
            
        return headers
    @staticmethod
    def get_test_numbers(df): 
        """
        Get the list of test numbers from the dataframe.

        Parameters:
            df (pd.DataFrame): The input dataframe.

        Returns:
            list: A list of test names extracted from the dataframe columns.

        Raises:
            ValueError: If no test names are found in the dataframe.
        
        Example:
            >>> test_numbers = EFF.get_test_numbers(df)
            ['4033', '2003', '4004', '2029', '3210', .... ,'4026', '3133']
        """
        try:
            data = get_test_numbers_row(df)
            test_names = [col for col in data if str(col).isdigit()]
            if not test_names:
                raise ValueError("No test numbers found in the dataframe.")
            return list(set(test_names))
        except Exception as e:
            print(f"Error occurred while getting test names: {e}")
            return None
    @staticmethod
    def get_value_rows(df, fix_dtypes=False, header = None): # Robust # Verified
        """
        Extracts the value rows in a DataFrame that contain measurement data.

        Parameters:
            df: pandas.DataFrame
                Input pandas DataFrame from which measurement data is extracted.
            fix_dtypes: bool, optional
                Whether to fix the data types of the extracted DataFrame based on a specific row in the input DataFrame.
                Default is False.
            header: str, optional
                If a specific row label is provided, that row will be used as column headers.
                If None, the header will be inferred from the input DataFrame.
                If 'auto', the row containing the test numbers will be used as column headers. 


        Returns:
            pandas.DataFrame
                A DataFrame that only includes the rows with measurement data.

        Raises:
            TypeError
                If the input is not a pandas DataFrame.
            ValueError
                If the provided header is not found in the input DataFrame.

        Notes:
            - If `fix_dtypes` is True, the data types of the returned DataFrame will be corrected based on the specified data type row in the input DataFrame.

        Examples: 
            >>> df, metadata = read('path/to/file.eff')
            >>> data = EFF.get_value_rows(df, header = "<+EFF:1.00>")
            >>> data.head()
            ... <+EFF:1.00>  Lot    Split  Wafer X     Y     VNr  Date      Device   Process YIO5A:XLoc YIO5A:YLoc YIO5A:XSize YIO5A:YSize YBS3:Yield  
            ... 20_Lot       A53789 .01                           2000-03-28 256M_D17 PLY                                                   5.791E+01  
            ... 15_Waf       A53789 .01    12                     2000-03-28 256M_D17 PLY                                                   3.875E+01  
            ... 05_Die       A53789 .01    12    22    10    01   2000-03-28 256M_D17 PLY     855372     758473     123         399                    
            ... 05_Die       A53789 .01    12    22    10    02   2000-03-28 256M_D17 PLY     322456     150023     567         201                    
            ... 05_Die       A53789 .01    12    22    10    03   2000-03-28 256M_D17 PLY     145567     988344     12          321                    
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError('Input must be a pandas DataFrame.')
        
        data = df.iloc[get_values_rows_index(df):,:].copy()

        if header is not None:
            if header == "auto":
                data.columns = get_test_numbers_row(df)
            else: 
                try:
                    data.columns = get_row(df, header)
                except KeyError:
                    print(f"Error: Header '{header}' not found in the input DataFrame.")
            
        if fix_dtypes:
            return correct_types(data)

        return data