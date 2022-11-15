import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt



def load_transform(
        path_to_data, 
        start_date = "2021-10-01", 
        end_date = "2022-09-30", 
        drop = True, 
        verbos = False
        ):
    """load pedestrian count data and set index as date
    -----------------------------------------------------
    Args:
        path_to_data: str
            path to data set
        start_date: str
            start date for the analysos period, default: "2021-10-01"
        end_date: str
            end date for the analysos period, default: "2022-09-30"
        drop: bool 
            drop unused columns, default: True
        verbos: bool
            print range of date and intersection names, default: False
    Returns:
        df: DataFrame
            the loaded transformed dataframe
    """
    # load csv file
    df = pd.read_csv(path_to_data, delimiter=';')

    # Combine date/time columns and change the type to datetime 
    df['date'] = pd.to_datetime(df['date'] + ' ' + df['time'], format='%Y-%m-%d %H:%M:%S')

    # Set index as date column and sort
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)

    # keep one year count data given start and end dates
    df = df[(df.index >= start_date) & (df.index <= end_date)]

    # Drop unused columns
    if drop:
        df.drop(columns=['latitude', 'longitude', 'time'], inplace=True)

    if verbos:
        # Show the date range
        print(f'Data From {df.index.min()} to {df.index.max()}')
        # Show unique intersections names
        print(df.name.unique())
    return df


def plot_ts(df_int,
            agg_level = 'D', 
            show_stat=False
            ):
    """
    plot ped counts for a given the intersection with given aggreagate level
    ------------------------------------------------------------------------
    Args:
        df_int: DataFrame
            dataset for the given intersections for the analysis period
        agg_level: str
            aggregation level for plotting (Daily: D, Weekly: W, Monthly: M), defualt: D
        show_stat: bool
            show the statistics for the data set for given intersection, default: False

    Returns:
        None
    """

    # Resample data to get daily or weekly or monthly counts
    df_int_r = df_int.resample(agg_level).sum()

    # Summary statistics
    if show_stat:
        print(df_int_r.describe())

    # Plotting the time series of Ped counts for each crossing
    fig, axs = plt.subplots(1, figsize=(12, 4))
    fig.suptitle('Time series of pedestrian volume - ' + agg_level)

    df_int_r.ped_N.plot(ax=axs)
    df_int_r.ped_S.plot(ax=axs)
    df_int_r.ped_E.plot(ax=axs)
    df_int_r.ped_W.plot(ax=axs)
    axs.legend()
    plt.show()


def get_24h_count_df(data, 
                    intersection_name, 
                    H15=100, 
                    H24=500, 
                    T24=72,
                    verbos=False
                    ):
    """
    Filter invalid 15min and 24h counts and return aggregated 24h counts
    ------------------------------------------------------------------------
    Args:
        data: DataFrame
            dataset for all intersections for the analysis period
        intersection_name: str
            name of intersection of interest
        H15: int
            Hardcap (upper limit) value for 15min count, defualt: 100
        H24: int
            Hardcap (upper limit) value for 24h count, defualt: 500
        T24: int
            Min (lower limit) value for 24hcount, defualt: 72
        verbos: bool
            print number of filtered rows for each filter, defualt: False
    
    Returns:
        df_int_24h: DataFrame
            24h ped count dataframe based on valid counts
    """
    # take the data for the given intersection
    df_int = data.loc[data['name'] == intersection_name, :].copy()

    # F1: flag rows with all counts equalt to zero as missing values
    columns = ['ped_N', 'ped_S', 'ped_W', 'ped_E', 'vol_vehicle']
    df_int['F1'] = (df_int[columns]==0).all(axis=1)

    # F2: flag rows with any 15min count greater than H15 on crossing, hard-cap filter 
    columns = ['ped_N', 'ped_S', 'ped_W', 'ped_E']
    df_int['F2'] = (df_int[columns]>H15).any(axis=1)
    

    # Compute 24h volume on each crossing
    df_int_24h = df_int.loc[(df_int.F1==False) & (df_int.F2==False), :].copy()
    df_int_24h = df_int.resample('D').sum(numeric_only=True)
    df_int_24h['num_valid_counts'] = df_int.vol_vehicle.resample('D').count()

    # Adjust the aggregated counts using factors
    df_int_24h['ped_N'] = df_int_24h.ped_N / df_int_24h.num_valid_counts * 96
    df_int_24h['ped_S'] = df_int_24h.ped_S / df_int_24h.num_valid_counts * 96
    df_int_24h['ped_W'] = df_int_24h.ped_W / df_int_24h.num_valid_counts * 96
    df_int_24h['ped_E'] = df_int_24h.ped_E / df_int_24h.num_valid_counts * 96

    # F3: flag rows with valid 24h volume estimate considering T24
    df_int_24h['F3'] = (df_int_24h['num_valid_counts']<T24)

    # F4: flag rows with any 24h volumes greater than H24, hard-cap filter for crossing
    df_int_24h['F4'] = (df_int_24h[columns]>H24).any(axis=1)

    if verbos:
        print("\n", intersection_name)
        print(f"# of flagged rows with F1 (missing): {df_int.F1.sum()}")
        print(f"# of flagged rows with F2 (more than H15): {df_int.F2.sum()}")
        print(f"# of flagged rows with F3 (less than T24): {df_int_24h.F3.sum()}")
        print(f"# of flagged rows with F4 (more than H24): {df_int_24h.F4.sum()}")
    
    return df_int_24h.loc[(df_int_24h.F3==False) & (df_int_24h.F4==False), :]


def get_AADPT(df_int_24h, count_col='ped_N'):
    """
    Calculates AADPT for a given valid 24h counts for an intersection
    ------------------------------------------------------------------------
    Args:
        df_int_24h: DataFrame
            dataset with valid 24h count for an intersection
        count_col: str
            name of column for the crossing of interest
    Returns:
        AADPT: float
            Average annual daily pedestrian traffic
    """
    # n_j: Number of months-of-year m for which there is at least one valid 24h volume
    # n_jm: Number of days-of-week d in month-of-year m for which there is least one valid 24h volume
    # n_jmd: Number of valid 24h volume for day-of-week d in month-of-year m at location j
    # V_jmdi: 24h volume at location j on the i-th occurrence of day-of-week d in month m
    months = df_int_24h.index.month.unique()
    dayofweeks = df_int_24h.index.dayofweek.unique()
    n_j = len(months)       
    n_jm = len(dayofweeks)
    AADPT = 0
    for m in months:
        for d in dayofweeks:
            volumes = df_int_24h[(df_int_24h.index.month == m) & (df_int_24h.index.dayofweek == d)][count_col].values
            sum_V_jmdi = sum(volumes)
            n_jmd = len(volumes)
            if n_jmd !=0:
                AADPT += 1/n_j * 1/n_jm * 1/n_jmd * sum_V_jmdi
    return AADPT

def get_true_ratio(df_int_24h):
    """
    Calculates true AADPT ratios for crossings
    ------------------------------------------------------------------------
    Args:
        df_int_24h: DataFrame
            dataset with valid 24h count for an intersection
    Returns:
        AADPT_tot: float
            total AADPT
        ratio_N_true: float
            True AADPT ratio for north crossing 
        ratio_S_true: float
            True AADPT ratio for south crossing
        ratio_W_true: float
            True AADPT ratio for west crossing
        ratio_E_true: float
            True AADPT ratio for east crossing
    """
    # average annual daily pedestrian traffic
    AADPT_N = get_AADPT(df_int_24h, 'ped_N')
    AADPT_S = get_AADPT(df_int_24h, 'ped_S')
    AADPT_W = get_AADPT(df_int_24h, 'ped_W')
    AADPT_E = get_AADPT(df_int_24h, 'ped_E')
    AADPT_tot = AADPT_N + AADPT_S + AADPT_W + AADPT_E

    # true volume ratios 
    ratio_N_true = 0 if AADPT_tot==0 else AADPT_N / AADPT_tot 
    ratio_S_true = 0 if AADPT_tot==0 else AADPT_S / AADPT_tot 
    ratio_W_true = 0 if AADPT_tot==0 else AADPT_W / AADPT_tot 
    ratio_E_true = 0 if AADPT_tot==0 else AADPT_E / AADPT_tot 

    res = AADPT_tot, ratio_N_true, ratio_S_true, ratio_W_true, ratio_E_true
    return res


def get_8h_count_df(data,
                    intersection_name,
                    holidays, 
                    verbos=False
                    ):
    """
    returns the dataframe with 8 hour counts for valid short-term counts days
    ------------------------------------------------------------------------
    Args:
        data: DataFrame
            dataset for all intersections for the analysis period
        intersection_name: str
            name of intersection of interest
        holidays: List (str)
            list of dates that are holidays in the given data set
        verbos: bool
            print number of unique hours, day of weeks, and Months, default: False

    Returns:
        df_int_8h: DataFrame
            8h ped count dataframe for valid days for short-term counts
    """
    # take the data for the given intersection
    df_int = data[data['name'] == intersection_name]

    # Resample data to get Hourly counts
    df_int_stc_h = df_int.resample('H').sum(numeric_only=True)

    # Keep valid hours for short-term count 7am-9am, 11am-2pm, 3pm-6pm
    df_int_h_valid = pd.concat([df_int_stc_h.between_time('7:00', '9:00'),
                                    df_int_stc_h.between_time('11:00', '14:00'),
                                    df_int_stc_h.between_time('15:00', '18:00')])
    
    # Resample data to get 8h short-term counts
    df_int_8h = df_int_h_valid.resample('D').sum(numeric_only=True)

    # Keep valid months (4,5,6,9,10,11) and day of weeks Tuesdays (1), Wednesdays (2), and Thursdays (3)
    df_int_8h = df_int_8h[df_int_8h.index.dayofweek.isin([1,2,3]) &
                          df_int_8h.index.month.isin([4,5,6,9,10,11])]

    # Exclude the holidays
    df_int_8h = df_int_8h[~df_int_8h.index.isin(holidays)]

    # drop those days with zero total counts
    df_int_8h['total'] = df_int_8h.ped_N + df_int_8h.ped_S + df_int_8h.ped_W + df_int_8h.ped_E
    df_int_8h.drop(df_int_8h[df_int_8h.total == 0].index, inplace=True)

    # check if filters worked
    if verbos:
        print(f'valid STC: {len(df_int_8h)}, droped zero counts: {len(df_int_8h[df_int_8h.total == 0])}')
        print('Hours: ', df_int_h_valid.index.hour.unique())
        print('Day of Weeks: ', df_int_8h.index.day_of_week.unique())
        print('Months: ', df_int_8h.index.month.unique())

    return df_int_8h



def get_ratio_errors(df_int_8h, 
                    df_int_24h,
                    stc_num = 1,
                    repeat = 100):
    """
    returns the list of avg error for crossing ratio estimates based on 
    a give number of short-term counts for a given repeat size

    -------------------------------------------------------------------
    Args:
        df_int_8h: DataFrame
            8h ped count dataframe for valid days for short-term counts
        intersection_name: str
            name of intersection of interest
        holidays: List (str)
            list of dates that are holidays in the given data set
        verbos: bool
            print number of unique hours, day of weeks, and Months, default: False

    Returns:
        error_df: DataFrame
            includes following columns
                ratio_avg_errs: avg of abs value of error ratio for all crossing
                ratio_N_errs: error ratio for north crossing
                ratio_S_errs: error ratio for south crossing
                ratio_W_errs: error ratio for west crossing
                ratio_E_errs: error ratio for east crossing 
    """
    # calculate true ratios
    _, ratio_N_true, ratio_S_true, ratio_W_true, ratio_E_true = get_true_ratio(df_int_24h)

    # make a copy of df_int_8h
    df_int_8h_ = df_int_8h.copy()

    if stc_num == 1:
        # volume ratio for each approach
        df_int_8h_['ratio_N'] = df_int_8h_.ped_N / df_int_8h_.total
        df_int_8h_['ratio_S'] = df_int_8h_.ped_S / df_int_8h_.total
        df_int_8h_['ratio_W'] = df_int_8h_.ped_W / df_int_8h_.total
        df_int_8h_['ratio_E'] = df_int_8h_.ped_E / df_int_8h_.total

        # volume ratio error for each approach
        df_int_8h_['ratio_N_err'] = (df_int_8h_.ratio_N - ratio_N_true)/(ratio_N_true + 0.0001)
        df_int_8h_['ratio_S_err'] = (df_int_8h_.ratio_S - ratio_S_true)/(ratio_S_true + 0.0001)
        df_int_8h_['ratio_W_err'] = (df_int_8h_.ratio_W - ratio_W_true)/(ratio_W_true + 0.0001)
        df_int_8h_['ratio_E_err'] = (df_int_8h_.ratio_E - ratio_E_true)/(ratio_E_true + 0.0001)

        df_int_8h_['ratio_avg_err'] = 0.25*(abs(df_int_8h_['ratio_E_err'])+abs(df_int_8h_['ratio_W_err'])+
                                            abs(df_int_8h_['ratio_N_err'])+abs(df_int_8h_['ratio_N_err']))
        
        ratio_avg_errs = df_int_8h_['ratio_avg_err'].values
        ratio_N_errs = df_int_8h_['ratio_N_err'].values
        ratio_S_errs = df_int_8h_['ratio_S_err'].values
        ratio_W_errs = df_int_8h_['ratio_W_err'].values
        ratio_E_errs = df_int_8h_['ratio_E_err'].values
        
    
    else:
        ratio_N_errs = []
        ratio_S_errs = []
        ratio_W_errs = []
        ratio_E_errs = []
        ratio_avg_errs = []
        for _ in range(repeat):
            # draw stc days and sum counts
            sample_stc = df_int_8h.sample(n=stc_num, replace=False).sum()

            # compute error for each crossing ratio
            ratio_N_err = (sample_stc.ped_N/sample_stc.total - ratio_N_true)/(ratio_N_true + 0.0001)
            ratio_S_err = (sample_stc.ped_S/sample_stc.total - ratio_S_true)/(ratio_S_true + 0.0001)
            ratio_W_err = (sample_stc.ped_W/sample_stc.total - ratio_W_true)/(ratio_W_true + + 0.0001)
            ratio_E_err = (sample_stc.ped_E/sample_stc.total - ratio_E_true)/(ratio_E_true + 0.0001)

            # average the ratio errors and append to the error list
            ratio_avg_err = 0.25 * (abs(ratio_N_err) + abs(ratio_S_err) + \
                                    abs(ratio_W_err) + abs(ratio_E_err))
            
            # append to the resuls list
            ratio_N_errs.append(ratio_N_err)
            ratio_S_errs.append(ratio_S_err)
            ratio_W_errs.append(ratio_W_err)
            ratio_E_errs.append(ratio_E_err)
            ratio_avg_errs.append(ratio_avg_err)

    error_df = pd.DataFrame()
    error_df['ratio_N_errs'] = ratio_N_errs
    error_df['ratio_S_errs'] = ratio_S_errs
    error_df['ratio_W_errs'] = ratio_W_errs
    error_df['ratio_E_errs'] = ratio_E_errs
    error_df['ratio_avg_errs'] = ratio_avg_errs


    return error_df


def get_confidence_interval(errs, percentile = 85):
    """
    calculates 95% confidence intervall and 85th percentile in given error array

    -------------------------------------------------------------------
    Args:
        errs: Numpy.array
            array of ratio errors

    Returns:
        lcb: float
            lower confidence bound
        mean: float
            mean value of errors
        ucb: float
            upper confidence bound
        nth_percentile: float
            nth percentile value given percentile param
    """
    mean = np.mean(errs)
    sd = np.std(errs)
    n = len(errs)
    Zstar=1.65

    lcb = mean - Zstar * sd
    ucb = mean + Zstar * sd

    nth_percentile = np.percentile(errs, percentile)
    
    return round(lcb,3), round(mean,3), round(ucb,3), round(nth_percentile,3)

