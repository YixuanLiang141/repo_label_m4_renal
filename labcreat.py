import pandas as pd

def filter_large_csv_by_stay_ids(input_file, output_file, key_col, chunksize=100_000):
    # 52024 is whole blood, 52546 are all nan
    valid_ids = [50912, 52024, 52546]

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

def remove_columns_from_csv(data_file, output_file):

    df = pd.read_csv(data_file)

    df = df[["subject_id", "itemid", "charttime", "value"]]
    df.rename(columns={'itemid': 'wholeblood'}, inplace=True)

    mapping = {50912: 0, 52024: 1, 52546: 0}
    df["wholeblood"] = df["wholeblood"].map(mapping).fillna(df["wholeblood"])

    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['value'])

    mask = (df['value'] > 100) | (df['value'] < 0)
    df = df[~mask]

    df.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":

    #filter_large_csv_by_stay_ids('../../hosp/labevents.csv', './labcreat.csv', 'itemid')
    remove_columns_from_csv('./labcreat.csv', './labcreat.csv')