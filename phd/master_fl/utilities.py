import csv, os

def append_record_to_csv(file_path, record):
    # Ensure the record is structured correctly (e.g., string)
    if not isinstance(record, str):
        raise ValueError("Record must be a string")

    # Open the file in append mode ('a')
    with open(file_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        print(f"{record} has been recorded")
        
        # Check if file is empty
        if csvfile.tell() == 0:
            # If empty, write header first (assuming it's ["Nodename"])
            writer.writerow(["Nodename"])
        
        # Convert the string to a list for writing to CSV
        writer.writerow([record])

def delete_files_in_folder(folder_path):
    """
    Delete all files from acpu_query = f'sum(irate(node_cpu_seconds_total{{mode="user",instance="{node_ip}:9100"}}[1m]))' folder.

    Args:
    - folder_path (str): The path to the folder containing the files to be deleted.
    """
    # Get a list of all files in the folder
    files = os.listdir(folder_path)
    
    # Iterate over each file and delete it
    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        try:
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
        except OSError as e:
            print(f"Error: {e.strerror}")

def delete_file(file_name):
    while True:
        try:
            # Check if the file exists
            if os.path.exists(file_name):
                # Delete the file
                os.remove(file_name)
                break
            else:
                print(f"The file '{file_name}' does not exist.")

        except Exception as e:
            print(f"An error occurred: {e}")

def count_files_with_word(directory, word):
    """
    Count the number of files in a directory that contain a specific word in their names.

    Args:
    - directory (str): The path to the directory.
    - word (str): The word to search for in the file names.

    Returns:
    - int: The number of files containing the word in their names.
    """
    count = 0
    for file_name in os.listdir(directory):
        if word in file_name:
            count += 1
    return count

def list_files_with_word(directory, word):
    """
    List the files in a directory that contain a specific word in their names.

    Args:
    - directory (str): The path to the directory.
    - word (str): The word to search for in the file names.

    Returns:
    - list: A list containing the names of files with the specified word in their names.
    """
    # Get a list of all files in the specified directory
    files_in_directory = os.listdir(directory)
    
    # Filter out only the files containing the specified word in their names
    files_with_word = [file for file in files_in_directory if os.path.isfile(os.path.join(directory, file)) and word in file]

    return files_with_word