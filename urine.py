import pandas as pd

def filter_large_csv_by_stay_ids(input_file, output_file, key_col, chunksize=100_000):
    valid_ids = [226559, 226560, 226561, 226584, 226563, 226564,
                 226565, 226567, 226557, 226558, 227488, 227489]

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

    df = df[["subject_id", "charttime", "itemid", "value"]]

    df.to_csv(output_file, index=False)
    print(f"输出文件保存至：{output_file}")

def process_gu_irrigation(
    input_path="input.csv",
    output_path="output.csv"
):
    df = pd.read_csv(input_path)

    # 确保 value 可以进行数值计算
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # 用于识别 227488 / 227489
    target_itemids = {227488, 227489}

    # 保存需要删除的原始行索引
    rows_to_drop = []

    # 保存需要修改的 227489 行：
    # index -> (new_itemid, new_value)
    rows_to_modify = {}

    # 只检查包含 227488 / 227489 的记录
    target_mask = df["itemid"].isin(target_itemids)

    for (subject_id, charttime), group in df[target_mask].groupby(
        ["subject_id", "charttime"],
        dropna=False
    ):
        # 只有恰好两行时才进行配对处理
        if len(group) != 2:
            continue

        itemids = group["itemid"].tolist()

        # 必须恰好一个 227488 + 一个 227489
        if set(itemids) != {227488, 227489}:
            continue

        row_488 = group[group["itemid"] == 227488].iloc[0]
        row_489 = group[group["itemid"] == 227489].iloc[0]

        value_488 = row_488["value"]
        value_489 = row_489["value"]

        # 如果 value 缺失，则不处理
        if pd.isna(value_488) or pd.isna(value_489):
            continue

        if value_489 > value_488:
            # 227489 - 227488
            new_value = value_489 - value_488

            # 删除 227488
            rows_to_drop.append(row_488.name)

            # 227489 改成 227490，并更新 value
            rows_to_modify[row_489.name] = (227490, new_value)

        else:
            # 227489 <= 227488
            # 两行全部删除
            rows_to_drop.extend([row_488.name, row_489.name])

    # 删除需要删除的行
    df = df.drop(index=rows_to_drop)

    # 修改需要转换成 227490 的行
    for idx, (new_itemid, new_value) in rows_to_modify.items():
        if idx in df.index:
            df.loc[idx, "itemid"] = new_itemid
            df.loc[idx, "value"] = new_value

    # 删除剩余的行
    target_mask = df["itemid"].isin(target_itemids)
    df = df[~target_mask]

    # 保存
    df.to_csv(output_path, index=False)

    print("Done")

def sort_csv_by_two_col(input_file, output_file, col1, col2):
    df = pd.read_csv(input_file)
    df.sort_values(by=[col1, col2], inplace=True)
    df.to_csv(output_file, index=False)

if __name__ == "__main__":

    filter_large_csv_by_stay_ids('../../icu/outputevents.csv', './urine.csv', 'itemid')
    remove_columns_from_csv('./urine.csv', './urine.csv')
    process_gu_irrigation('./urine.csv', './urine.csv')
    sort_csv_by_two_col('./urine.csv', './urine.csv', 'subject_id', 'charttime')