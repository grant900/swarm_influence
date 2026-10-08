def column_means(text: str) -> dict:
    lines = text.strip().split("\n")
    header = lines[0].split(",")
    sums = {h: 0.0 for h in header}
    for line in lines[1:]:
        for h, v in zip(header, line.split(",")):
            sums[h] += float(v)
    return {h: sums[h] / len(lines) for h in header}
