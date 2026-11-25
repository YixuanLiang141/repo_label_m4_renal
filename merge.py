import pandas as pd

def merge_sort(csv1: str, csv2: str, output_file: str):

    df1 = pd.read_csv(csv1)
    df2 = pd.read_csv(csv2)

    if set(df1.columns) != set(df2.columns):
        raise ValueError("Different columns in inputs")

    merged_df = pd.concat([df1, df2], ignore_index=True)

    merged_df.sort_values(by=['subject_id', 'charttime'], inplace=True)

    merged_df = merged_df.drop_duplicates(keep='first')

    merged_df.to_csv(output_file, index=False)

    print(f"Result saved to: {output_file}")

if __name__ == "__main__":
    merge_sort('./chartcreat.csv', './labcreat.csv', './creatinine.csv')