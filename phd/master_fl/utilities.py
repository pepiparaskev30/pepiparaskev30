import csv, os

def append_record_to_csv(file_path, record):
    # Ensure the record is structured correctly (e.g., list of values)
    if not isinstance(record, list):
        raise ValueError("Record must be a list")

    # Open the file in append mode ('a')
    with open(file_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        print(f"{record} has been recorded")
        
        # Check if file is empty
        if csvfile.tell() == 0:
            # If empty, write header first (assuming it's ["Nodename"])
            writer.writerow(["Nodename"])
        
        writer.writerow(record)