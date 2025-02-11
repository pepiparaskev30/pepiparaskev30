import csv

def append_to_csv_nodes(NODE_NOTBOOK_DIR,node_name):
    file_path = NODE_NOTBOOK_DIR+"/"+f"nodes_notebook.csv"
    with open(file_path, 'a', newline='') as csvfile:
        fieldnames = ['Nodename']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # If the file is empty, write the header
        if csvfile.tell() == 0:
            writer.writeheader()

        # Append the metrics
        writer.writerow({'Nodename': node_name})