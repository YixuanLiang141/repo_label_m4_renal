import pandas as pd

def filter_large_csv_by_stay_ids(input_file, output_file, key_col, chunksize=100_000):
    valid_ids = [220615, 229761]

    reader = pd.read_csv(input_file, chunksize=chunksize)
    first_chunk = True

    total_rows_kept = 0
    for i, chunk in enumerate(reader):
        filtered_chunk = chunk[chunk[key_col].isin(valid_ids)]
        total_rows_kept += len(filtered_chunk)

        if first_chunk:
            filtered_chunk.to_csv(output_file, index=False, mode='w')
            first_chunk = False
        else:
            filtered_chunk.to_csv(output_file, index=False, mode='a', header=False)

        print(f"✔ 已处理第 {i+1} 块，保留 {len(filtered_chunk)} 行")

    print(f"🎉 筛选完成，最终保留 {total_rows_kept} 行，保存至 {output_file}")

def delete_rows_by_values(input_file, output_file):
    df = pd.read_csv(input_file)
    mask = (df['value'] > 100) & (df['valueuom'].isna())
    df = df[~mask]
    df.to_csv(output_file, index=False)

def remove_columns_from_csv(data_file, output_file):

    df = pd.read_csv(data_file)

    df = df[["subject_id", "charttime", "itemid", "value"]]

    df.to_csv(output_file, index=False)
    print(f"输出文件保存至：{output_file}")

if __name__ == "__main__":

    #filter_large_csv_by_stay_ids('../../icu/chartevents.csv', './chartcreat.csv', 'itemid')
    #delete_rows_by_values('./chartcreat.csv', './chartcreat.csv')
    remove_columns_from_csv('./chartcreat.csv', './chartcreat.csv')
