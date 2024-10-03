import os
import re
import pandas as pd

def parse_imgt_fasta(infile):
    '''Extract gene names from an IMGT reference fasta.

    :param infile: IMGT reference fasta for TRAV, TRAJ, TRBV, or TRBJ
    :type infile: str
    :return: Gene names
    :rtype: list
    '''
    
    # Read the file and extract lines starting with ">"
    with open(infile, "r") as f:
        lines = f.readlines()

    # Extract the second element from lines starting with ">"
    imgt_list = []
    for line in lines:
        if line.startswith(">"):
            gene = line.split("|")[1]
            imgt_list.append(gene)

    return imgt_list


def extract_imgt_genes(data_dir):
    '''Extract gene names from all IMGT reference fasta files in a folder.

    :param data_dir: Directory containing IMGT reference fasta files
    :type data_dir: str
    :return: Gene names
    :rtype: dataframe
    '''

    fastas = []
    for file in os.listdir(data_dir):
        if file.endswith('.fa') | file.endswith('.fasta'):
            fastas.append(data_dir + file)

    # Extract gene names and put into a dataframe
    imgt = []
    for fa in fastas:
        imgt = imgt + parse_imgt_fasta(fa)
    lookup = pd.DataFrame({'imgt': imgt})
    lookup_sorted = lookup.sort_values('imgt').reset_index(drop=True)

    return lookup_sorted


def add_dash_one(s):
    '''Add a '-01' to genes without gene-level designatinon in IMGT (e.g. human TRBV2)

    :param s: Gene name
    :type s: str
    :return: Gene name containing '-01' only if no '-' originally
    :rtype: str
    '''
    if '-' not in s:
        # Add -1 before allele
        return s.replace('*', '-01*')
    return s


def pad_single_digit(s):
    '''Add a zero to single-digit gene names to match double-digit adaptive format.

    :param s: Gene name containing double and/or single-digit numbers
    :type s: str
    :return: Gene name containing double-digit numbers
    :rtype: str
    '''
    # Use regex to find a single digit preceded by letters and followed by a hyphen or asterisk
    updated_string = re.sub(r'([A-Za-z]+)(\d)([-\*])', r'\g<1>0\g<2>\g<3>', s)
    return updated_string


def build_lookup_from_fastas(data_dir):
    '''Runs all functions necessary to make a lookup table.

    :param data_dir: Directory containing IMGT reference fasta files
    :type data_dir: str
    :return: None
    '''

    # Extract IMGT gene names and put into a dataframe
    lookup = extract_imgt_genes(data_dir)

    # Create 10X column by removing allele info (e.g. *01) and slash from "/DV"
    lookup['tenx'] = lookup['imgt'].apply(lambda x: x[:-3].replace('/DV', 'DV'))

    # Create Adaptive columns by adding letters, 0's, removing /DV and renaming /OR
    lookup['adaptive'] = lookup['imgt'].apply(lambda x: x.\
                                            replace('TRAV14/DV4', 'TRAV14-1').\
                                            replace('TRAV23/DV6', 'TRAV23-1').\
                                            replace('TRAV29/DV5', 'TRAV29-1').\
                                            replace('TRAV36/DV7', 'TRAV36-1').\
                                            replace('TRAV38-2/DV8', 'TRAV38-2').\
                                            replace('TRAV4-4/DV10', 'TRAV4-4/').\
                                            replace('TRAV6-7/DV9', 'TRAV6-7').\
                                            replace('TRAV13-4/DV7', 'TRAV13-4').\
                                            replace('TRAV14D-3/DV8', 'TRAV14D-3').\
                                            replace('TRAV15D-1/DV6D-1', 'TRAV15D-1').\
                                            replace('TRAV15-1/DV6-1', 'TRAV15-1').\
                                            replace('TRAV16D/DV11', 'TRAV16D-1').\
                                            replace('TRAV21/DV12', 'TRAV21-1').\
                                            replace('TRAV15-2/DV6-2', 'TRAV15-2').\
                                            replace('TRAV15D-2/DV6D-2', 'TRAV15D-2').\
                                            replace('TR', 'TCR').\
                                            replace('-', '-0').\
                                            replace('/OR9-02', '-or09_02'))
    lookup['adaptive'] = lookup['adaptive'].apply(lambda x: add_dash_one(x))
    lookup['adaptive'] = lookup['adaptive'].apply(lambda x: pad_single_digit(x))
    lookup['adaptivev2'] = lookup['adaptive']

    # Set Adaptive columns to NA for constant genes (Adaptive only captures VDJ)
    lookup.loc[lookup['imgt'].str.contains('C'), ['adaptive', 'adaptivev2']] = 'NoData'

    # If converting from 10X will just need the first *01 allele
    from_tenx = lookup.groupby('tenx').first().reset_index()

    # Make table for Adaptive genes with or without allele
    lookup2 = lookup[~lookup.adaptivev2.str.contains('NoData')]
    from_adapt = lookup2[['adaptivev2', 'imgt', 'tenx']]
    from_adapt['adaptive'] = from_adapt['adaptivev2'].apply(lambda x: x[:-3])
    from_adapt = from_adapt.drop(columns='adaptivev2').groupby('adaptive').first().reset_index()
    from_adapt['adaptivev2'] = from_adapt['adaptive']
    from_adaptive = pd.concat([lookup2, from_adapt])[['adaptive', 'adaptivev2', 'imgt', 'tenx']]

    # Remove any duplicate rows and save
    lookup.drop_duplicates().to_csv(data_dir + '/lookup.csv', index=False)
    from_tenx.drop_duplicates().to_csv(data_dir + '/lookup_from_tenx.csv', index=False)
    from_adaptive.drop_duplicates().to_csv(data_dir + '/lookup_from_adaptive.csv', index=False)
