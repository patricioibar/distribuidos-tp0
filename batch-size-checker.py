import sys
import os
import csv

DATA_DIR = '.data'
HEADER_SIZE = 5

def parse_max_bytes(arg, unit):
    try:
        num = int(arg)
        if num <= 0:
            raise ValueError
        unit = unit.lower()
        if unit == 'kb':
            return num * 1000
        elif unit == 'kib':
            return num * 1024
        else:
            raise ValueError
    except Exception:
        print("Max bytes must be a positive integer and unit must be KB or KiB (e.g., 8 KiB or 10 KB).")
        sys.exit(1)

def get_args():
    if len(sys.argv) != 4:
        print("Usage: python batch-size-checker.py <batch_size> <max_bytes> <unit>")
        print("max_bytes should be a positive integer and unit should be KB or KiB (e.g., 8 KiB or 10 KB).")
        sys.exit(1)
    try:
        batch_size = int(sys.argv[1])
        if batch_size <= 0:
            raise ValueError
    except ValueError:
        print("Batch size must be a positive integer.")
        sys.exit(1)
    max_bytes = parse_max_bytes(sys.argv[2], sys.argv[3])
    return batch_size, max_bytes

def check_csv_batches(file_path, batch_size, max_bytes):
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        batch = []
        batch_bytes = HEADER_SIZE
        for row in reader:
            if len(batch) == batch_size:
                batch = []
                batch_bytes = HEADER_SIZE
                
            row_str = ','.join(row) + '\n'
            row_bytes = len(row_str.encode('utf-8'))
            
            if batch_bytes + row_bytes > max_bytes:
                print(f"File {file_path}: Batch of {batch_size} rows exceeds {max_bytes} bytes.")
                return False
            
            batch.append(row)
            batch_bytes += row_bytes
        if batch and (len(batch) > batch_size or batch_bytes > max_bytes):
            print(f"File {file_path}: Batch of {batch_size} rows exceeds {max_bytes} bytes.")
            return False
    return True

def main():
    batch_size, max_bytes = get_args()   
    all_ok = True
    for fname in os.listdir(DATA_DIR):
        if fname.endswith('.csv'):
            fpath = os.path.join(DATA_DIR, fname)
            if not check_csv_batches(fpath, batch_size, max_bytes):
                all_ok = False
    if all_ok:
        print("All CSV files can be batched within the specified limits.")

if __name__ == "__main__":
    main()