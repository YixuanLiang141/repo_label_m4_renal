import pandas as pd

def filter_large_csv_by_stay_ids(input_file, output_file, key_col, chunksize=100_000):
    # 229761 is whole blood
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

def process_columns_values(input_file, output_file):
    df = pd.read_csv(input_file)

    df = df[["subject_id", "charttime", "itemid", "value"]]
    df.rename(columns={'itemid': 'wholeblood'}, inplace=True)

    mapping = {220615: 0, 229761: 1}
    df["wholeblood"] = df["wholeblood"].map(mapping).fillna(df["wholeblood"])

    mask = (df['value'] > 100) | (df['value'] < 0)
    df = df[~mask]

    df.to_csv(output_file, index=False)
    print(f"Result saved to: {output_file}")
    
if __name__ == "__main__":

    #filter_large_csv_by_stay_ids('../../icu/chartevents.csv', './chartcreat.csv', 'itemid')
    process_columns_values('./chartcreat.csv', './chartcreat.csv')
