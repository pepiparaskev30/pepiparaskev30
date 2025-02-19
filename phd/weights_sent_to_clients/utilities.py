#!/usr/bin/env python
'''
# Maintainer: Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
# Role: Lead Developer
Copyright (c) 2023 Pepi Paraskevoulakou <e.paraskevoulakou@unipi.gr>
Licensed under the MIT License.
Source code development for the PhD thesis (mock of Data generator)
'''

####################################################################
'''
Utilities - support script for the receive_fed_weights_api.py pod
'''

# Import necessary Libriaries
import os

def delete_file(file_name):
    try:
        # Check if the file exists
        if os.path.exists(file_name):
            # Delete the file
            os.remove(file_name)
            print(f"The file '{file_name}' has been successfully deleted.")
        else:
            print(f"The file '{file_name}' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")
