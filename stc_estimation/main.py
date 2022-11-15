import numpy as np
import pandas as pd
import argparse
import utils
from tqdm import tqdm 


parser = argparse.ArgumentParser(description='Crossing AADPT estimation and collecting error results')
parser.add_argument('--dataset', default='milton',
                    help='city/region name from (milton, toronto, pima)')
parser.add_argument('--data-path', default='../data/',
                    help='path to datasets, holidays, and intersection names')
parser.add_argument('--out-path', default='./outs/',
                    help='path to where the results be saved')
parser.add_argument('--start-date', default='2021-10-01',
                    help='start date for the analysis period')
parser.add_argument('--end-date', default='2022-09-30',
                    help='end date for the analysis period')
parser.add_argument('--Max15min', type=int, default=100,
                    help='hard cap value for 15min counts')
parser.add_argument('--Max24h', type=int, default=500,
                    help='Max valid value for 24h counts')                   
parser.add_argument('--Min24h', type=int, default=72,
                    help='Min valid value for 24h counts')
parser.add_argument('--stc-num', type=int, default=1,
                    help='number of stc to be used for ratio estimation')
parser.add_argument('--repeat', type=int, default=100,
                    help='number of samples to be taken with given stc_num for ratio estimation')     
parser.add_argument('--percentile', type=int, default=85,
                    help='nth percentile for report error ratios')                
parser.add_argument('--verbos', default=False,
                    help='enables showing result in each step')
            
args = parser.parse_args()

# settings
dataset_name               = args.dataset
path_to_dataset            = args.data_path + dataset_name + '.csv'
path_to_intersection_names = args.data_path + dataset_name + '_intersections.csv'
path_to_holidays           = args.data_path + dataset_name + '_holidays.csv'
path_to_outs               = args.out_path

start_date, end_date       = args.start_date, args.end_date
H15, H24, T24              = args.Max15min, args.Max24h, args.Min24h
stc_num, repeat            = args.stc_num, args.repeat
nth_percentile             = args.percentile
verbos                     = args.verbos


def main():
    # load data 
    valid_intersections = pd.read_csv(path_to_intersection_names).values.reshape(-1)
    holidays = pd.read_csv(path_to_holidays).values.reshape(-1)
    data = utils.load_transform(path_to_dataset,
                                start_date = start_date, 
                                end_date = end_date, 
                                drop = True, 
                                verbos = verbos)


    int_counter = 0
    res_list = []
    error_df = pd.DataFrame([])

    for intersection_name in tqdm(valid_intersections):
        res = [intersection_name]

        # get "valid" 24h volume estimates
        df_int_24h = utils.get_24h_count_df(data, 
                                            intersection_name, 
                                            H15=H15, 
                                            H24=H24, 
                                            T24=T24,
                                            verbos=verbos) 

        # calculate true ratios
        AADPT, ratio_N_true, ratio_S_true, ratio_W_true, ratio_E_true = utils.get_true_ratio(df_int_24h)
        res += [len(df_int_24h), AADPT, ratio_N_true, ratio_S_true, ratio_W_true, ratio_E_true]
        
        # filter valid short-term counts
        df_int_8h = utils.get_8h_count_df(data,
                                        intersection_name,
                                        holidays, 
                                        verbos=verbos
                                        )
        if len(df_int_8h) == 0:
            continue
        
        # record size of valid stc counts
        res += [len(df_int_8h)]

        # get the ratio errors and corresponding
        error_df_int = utils.get_ratio_errors(df_int_8h, 
                                                df_int_24h,
                                                stc_num = stc_num,
                                                repeat = repeat)    
        
        # concat all error df for all intersections
        error_df_int['intersection'] = intersection_name
        error_df = pd.concat([error_df, error_df_int], axis = 0)

        # 95% CI for ratio errors
        for col in ['ratio_avg_errs', 'ratio_N_errs', 'ratio_S_errs', 
                        'ratio_W_errs', 'ratio_E_errs']:
            # compute lower/uper bounds, mean and nth percentile
            LB, AVG, UB, nth_per = utils.get_confidence_interval(error_df_int[col].values, percentile = nth_percentile)

            # record the LB, AVG, UB,  nth_per
            res += [LB, AVG, UB, nth_per]


        # count number of valid intersections
        int_counter += 1
        res_list.append(res)


    error_df.to_csv(path_to_outs + dataset_name + '_error_df.csv', index=False)
    res_df = pd.DataFrame(res_list, columns=[
                                            'intersection',    
                                            'valid_24h_counts',
                                            'AADPT',
                                            'ratio_N_true', 
                                            'ratio_S_true', 
                                            'ratio_W_true', 
                                            'ratio_E_true',
                                            'valid_8h_stc',
                                            'LB_avg_err', 'MEAN_avg_err', 'UB_avg_err', 'PTILE_avg_err',
                                            'LB_N_err', 'MEAN_N_err', 'UB_N_err', 'PTILE_N_err',
                                            'LB_S_err', 'MEAN_S_err', 'UB_S_err', 'PTILE_S_err',
                                            'LB_W_err', 'MEAN_W_err', 'UB_W_err', 'PTILE_W_err',
                                            'LB_E_err', 'MEAN_E_err', 'UB_E_err', 'PTILE_E_err',
                                            ])
    res_df.to_csv(path_to_outs + dataset_name + '_res_df.csv',index=False)
    print("# of intersections: ", int_counter)


if __name__ == '__main__':
    main()