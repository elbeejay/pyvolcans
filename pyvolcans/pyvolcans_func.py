# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 09:49:16 2020

@author: Pablo Tierz, John A. Stevenson, Vyron Christodoulou
         (British Geological Survey, The Lyell Centre,
         Edinburgh, UK).
"""

# set of functions related to the implementation of PyVOLCANS

# standard packages
import logging
import sys
import webbrowser
from pathlib import Path
from fractions import Fraction

# external packages
import numpy as np
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from pyvolcans import (load_tectonic_analogy,
                       load_geochemistry_analogy,
                       load_morphology_analogy,
                       load_eruption_size_analogy,
                       load_eruption_style_analogy,
                       load_volcano_names)

VOLCANO_NAMES = load_volcano_names()

#dictionary of weights for the criteria
WEIGHTS = {'tectonic_setting': 0.2, 'geochemistry': 0.2,
           'morphology': 0.2, 'eruption_size': 0.2, 'eruption_style': 0.2}

# loading all the data
ANALOGY_MATRIX = {'tectonic_setting': load_tectonic_analogy(),
                  'geochemistry': load_geochemistry_analogy(),
                  'morphology': load_morphology_analogy(),
                  'eruption_size': load_eruption_size_analogy(),
                  'eruption_style': load_eruption_style_analogy()
                  }


def _frac_to_float(value):
    """Take a string of decimal or fractional number (e.g. '0.5' or '1/2')
       and return the float representation."""
    if value is None:
        return None
    else:
        return float(Fraction(value))


def fuzzy_matching(volcano_name, limit=10):
    """
    List volcanoes with names most similar to volcano_name.

    :param volcano_name: str, name of volcano
    :param limit: int, number of values to return
    :return names: list of str of similar names
    """
    matches = process.extract(volcano_name, VOLCANO_NAMES[0], limit=limit,
                              scorer=fuzz.UQRatio)
    match_idx = [item[2] for item in matches]
    volcano_info = VOLCANO_NAMES.iloc[match_idx].rename(columns={0:'name',
                                                                 1:'country',
                                                                 2:'smithsonian_id'})
    return volcano_info.to_string(index=False)


def get_volcano_idx_from_number(volcano_number):
    """
       Input smithsonian id and get index of the volcano matrix
    """
    volcano_idx = VOLCANO_NAMES.loc[VOLCANO_NAMES[2] == volcano_number]
    if volcano_idx.empty:
        msg = ("Volcano number does not exist. "
               "Please provide a non-zero, positive, six digits number. To check for "
               "existing volcano numbers (VNUM), please visit www.volcano.si.edu")
        raise PyvolcansError(msg)

    return volcano_idx.index[0]


def get_volcano_idx_from_name(volcano_name):
    """
    Input is volcano name as text, output is the index
    of the row/column with the volcano in the matrix.
    """
    # we need to create a message error here: "Name provided doesn't exist.
    # #"Please double-check spelling (including commas, e.g. "Ruiz, Nevado del"
    # #and/or check name on www.volcano.si.edu"

    matched_volcanoes = match_name(volcano_name)
    volcano_index = matched_volcanoes.index[0]
    return volcano_index


def get_volcano_name_from_idx(volcano_idx):
    """
    Input is volcano index as a number, output is the name
    of the volcano of interest.
    NB. Is it better to use Python indexing (starting in zero) or not,
    if the 'volcano_idx' is input by the user?
    """
    # we need to create a message error here: "Volcano index out of bounds.
    # Please provide a non-zero, positive number smaller than 1439 (Number of
    # volcanoes in VOTW 4.6.7 database)."

    volcano_name = \
        VOLCANO_NAMES.iloc[volcano_idx, 0]

    return volcano_name


def get_volcano_number_from_name(volcano_name):
    """
    Input is volcano name as text, output is the volcano
    number as indicated in the GVP database.
    """
    # we need to create a message error here: "Name provided doesn't exist.
    # #"Please double-check spelling (including commas, e.g. "Ruiz, Nevado del"
    # #and/or check name on www.volcano.si.edu"

    matched_volcanoes = match_name(volcano_name)
    volcano_vnum = matched_volcanoes.iloc[0, 2]
    return volcano_vnum


def set_weights_from_args(args_dict):
    """
    If no arguments are specified everything is set to 0.2
    """
    no_values_set = all(value is None for value in args_dict.values())

    if no_values_set:
        args_dict = dict.fromkeys(args_dict.keys(), 0.2)
        return args_dict

    sum_of_weights = 0
    for key, value in args_dict.items():
        if value is None:
            args_dict[key] = 0
        else:
            sum_of_weights += value

    if sum_of_weights != 1:
        msg = f"Sum of weights ({sum_of_weights}) is different from 1!"
        raise PyvolcansError(msg)

    return args_dict


def calculate_weighted_analogy_matrix(weights,
                                      analogies=ANALOGY_MATRIX):
    """
    Input is dictionary of weights
    e.g. {‘tectonic_setting’: 0.5, ‘geochemistry’: 0.5}
    returns numpy array of weighted matrix.
    NB. We load all the matrices here inside the function
    """
    weighted_tectonic_analogy = \
        weights['tectonic_setting'] * analogies['tectonic_setting']

    weighted_geochemistry_analogy = \
        weights['geochemistry'] * analogies['geochemistry']

    weighted_morphology_analogy = \
        weights['morphology'] * analogies['morphology']

    weighted_eruption_size_analogy = \
        weights['eruption_size'] * analogies['eruption_size']

    weighted_eruption_style_analogy = \
        weights['eruption_style'] * analogies['eruption_style']

    weighted_total_analogy_matrix = weighted_tectonic_analogy + \
        weighted_geochemistry_analogy + weighted_morphology_analogy + \
        weighted_eruption_size_analogy + weighted_eruption_style_analogy

    return weighted_total_analogy_matrix


def get_analogies(my_volcano, weighted_analogy_matrix, count=10):
    """
    Returns, on screen, the names of the top <count> analogues to
    the target volcano (i.e. my_volcano) and their multi-criteria
    analogy values, as a variable: total_analogy.
    Default <count> = 10.
    """

    # get the index for my_volcano
    if isinstance(my_volcano, str):
        volcano_idx = get_volcano_idx_from_name(my_volcano)
    else:
        volcano_idx = get_volcano_idx_from_number(my_volcano)
    # calculate the <count> highest values of multi-criteria analogy
    # getting the row corresponding to the target volcano ('my_volcano')
    my_volcano_analogies = weighted_analogy_matrix[volcano_idx,]
    # adding 1 to 'count' to consider 'my_volcano' itself in the search
    count = count+1
    # getting the indices corresponding to the highest values of analogy
    # in descending order (highest analogy first)
    top_idx = my_volcano_analogies.argsort()[-count:][::-1]
    # removing 'my_volcano' from the list
    # top_idx = set(volcano_idx).symmetric_difference(top_idx)
    # np.argpartition(my_volcano_analogies, \
    # len(my_volcano_analogies) - count)[-count:]

    # obtain the volcano names and the analogy values
    top_analogies = my_volcano_analogies[top_idx]

    # print the names of the top <count> analogues
    # print(VOLCANO_NAMES.iloc[top_idx,2],VOLCANO_NAMES.iloc[top_idx,0:1],
    #     top_analogies)

    logging.debug("Top analogies: \n%s", VOLCANO_NAMES.iloc[top_idx, 0:3])

    # Prepare results table and print to standard output
    result = VOLCANO_NAMES.iloc[top_idx].copy()
    result.columns = ['name', 'country', 'smithsonian_id']
    result['analogy_score'] = top_analogies
    result.to_csv(sys.stdout, sep='\t', float_format='%.3f', header=True,
                  index=False, columns=('smithsonian_id', 'name', 'country',
                                        'analogy_score'))

    # anywhere 'volcano_idx' came from, make it a str
    volcano_name_csv = get_volcano_name_from_idx(volcano_idx)
    write_csv(volcano_name_csv, result, count)

    #open the GVP website of the top 1 analogue
    top_analogue_vnum = VOLCANO_NAMES.iloc[top_idx[1], 2] #[0]=target volcano!!
    my_web = f'https://volcano.si.edu/volcano.cfm?vn={top_analogue_vnum}' \
                '&vtab=GeneralInfo' #Getting to open the General Info tab
    webbrowser.open(my_web)

def write_csv(my_volcano, result, count):
    """
    TO DO!
    """
    # just adding the same line but outputting the list to a file [IMPROVE]
    # NB. {count - 1} because 'count' includes the target volcano!
    # processing the volcano name to make it more 'machine-friendly'
    my_volcano_clean = my_volcano.replace('\'', '').replace(',', '').replace('.', '')
    my_volcano_splitted = my_volcano_clean.split()
    my_volcano_joined = '_'.join(my_volcano_splitted)
    output_filename = Path.cwd() / f'{my_volcano_joined}_top{count-1}_analogues.csv'
    result.to_csv(output_filename, sep='\t', float_format='%.3f', header=True,
                  index=False, columns=('smithsonian_id', 'name', 'country',
                                        'analogy_score'))


def match_name(volcano_name):
    """Attempt to match name to Smithsonian catalogue."""
    matched_volcanoes = VOLCANO_NAMES.loc[VOLCANO_NAMES[0] == volcano_name]
    # throw errors whether if volcano does not exist
    # or there are 2+ identical names
    if len(matched_volcanoes) == 0:
        name_suggestions = fuzzy_matching(volcano_name)
        msg = (f"{volcano_name} not found! Did you mean:\n{name_suggestions}")
        raise PyvolcansError(msg)

    if len(matched_volcanoes) > 1:
        name_suggestions = fuzzy_matching(volcano_name)
        msg = (f"Volcano name {volcano_name} is not unique. "
               f"Please provide smithsonian id instead of name.\n{name_suggestions}")
        raise PyvolcansError(msg)

    return matched_volcanoes


def get_analogy_percentile(my_volcano, apriori_volcano,
                           weighted_analogy_matrix):
    """
    This function takes the target volcano (my_volcano), one 'a priori'
    analogue volcano (apriori_volcano), and the weighted analogy matrix
    calculated for the target volcano (weighted_analogy_matrix), and
    returns one percentile.
    This percentile corresponds to the analogy value between the
    target volcano and the a priori analogue within the distribution of
    analogy values between the target volcano and any Holocene volcano
    in the GVP database.
    :param my_volcano: str
    :param apriori_volcano: str
    :param weighted_analogy_matrix: numpy array
    :return percentile: float
    """
    # convert volcano names into inds to access the weighted_analogy_matrix
    my_volcano_idx = get_volcano_idx_from_name(my_volcano)
    apriori_volcano_idx = get_volcano_idx_from_name(apriori_volcano)

    # derive a vector with the analogy values for the target volcano
    my_analogy_values = weighted_analogy_matrix[my_volcano_idx,]

    # calculate percentiles from 0 to 100 (like in VOLCANS for now)
    analogy_percentiles = np.percentile(my_analogy_values,
                                        np.linspace(0, 100, 101),
                                        interpolation='midpoint')
    # find the closest value to the analogy of the a priori volcano
    # NOTE that this value already represents the percentile (0-100)
    my_percentile = (np.abs(analogy_percentiles - \
                            my_analogy_values[apriori_volcano_idx])).argmin()

    # Possible steps:
    return my_percentile

def get_many_analogy_percentiles(my_volcano, apriori_volcanoes_list,
                                 weighted_analogy_matrix):
    """
    This function takes the target volcano (my_volcano), a collection
    of one or more 'a priori' analogue volcanoes in a list
    (apriori_volcanoes_list), and the weighted analogy matrix calculated
    for the target volcano (weighted_analogy_matrix), and returns a
    collection of percentiles (as many as a priori analogues).
    These percentiles correspond to those of the analogy value between
    the target volcano and the a priori analogue within the distribution
    of analogy values between the target volcano and any Holocene volcano
    in the GVP database.
    :param my_volcano: str
    :param apriori_volcano: list of str
    :param weighted_analogy_matrix: numpy array
    :return percentile: dict of apriori volcano name and percentile
    :return better_analogues: dict of 'better analogues' name and percentage
    """

    # check a priori volcanoes is a list
    if not isinstance(apriori_volcanoes_list, list):
        raise PyvolcansError("A priori volcanoes should be a list!")

    percentile_dictionary = {}
    better_analogues_dictionary = {} # 100-percentile

    # loop over get_analogy_percentile
    for volcano in apriori_volcanoes_list:
        percentile = get_analogy_percentile(my_volcano, volcano,
                                            weighted_analogy_matrix)
        percentile_dictionary[volcano] = percentile
        better_analogues_dictionary[volcano] = 100 - percentile

    # adding a 'printing functionality' to the function
    print('\n\nAccording to PyVOLCANS, the following percentages of volcanoes'
          + ' in the GVP database\nare better analogues to {my_volcano:s}'
          + ' than the a priori analogues reported below:\n')
    for volcano, percentage in better_analogues_dictionary.items():
        print(f'{volcano:s}: {percentage:d}%\n')

    return percentile_dictionary, better_analogues_dictionary


class PyvolcansError(Exception):
    """Base class for all Pyvolcans errors"""
