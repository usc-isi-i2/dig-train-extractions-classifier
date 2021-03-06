import TextPreprocessors
import TokenSupervised
import ContextVectorGenerators
import os
import codecs
import sys
from sklearn.externals import joblib

TYPE = 'eye-color' #Default
GENERATE = 1

UNIGRAM_FILE = 'unigram-part-00000-v2.json'

DATA_FOLDER = 'annotated-cities-trial' #Should be present in the path of this file

# A supervised classification module that can be used for detecting wrong/right annotations

def data_preparation_for_training_data(training_file, embeddings_file, text_attribute, annotated_attribute,
                              correct_attribute, output_folder):
    """
    At present, this script cannot deal with multi-token annotations (e.g. 'Mary Ann' or 'Salt lake city'). We
    will convert all tokens to lower-case; thus, case-differences will not be accounted for.

    Two files will be written out to the output_folder, one of which will be intermediate, and the other of which
    is the file on which we will train/test the machine learning model.
    :param jlines_file: A file where each line is a json.
    :param embeddings_file: At present, use the provided file; do not try to generate it yourself
    :param text_attribute: e.g. 'high_recall_readability_text'
    :param annotated_attribute: e.g. 'annotated_cities'
    :param correct_attribute: e.g. 'correct_cities'
    :param output_folder: a folder for writing out files in
    :return: None
    """
    print ">>Data Preparation for Training Data<<"
    TextPreprocessors.TextPreprocessors.preprocess_annotated_file(training_file, text_attribute,
                                                                  output_folder+'tokens-file.jl')
    TokenSupervised.TokenSupervised.prep_preprocessed_annotated_file_for_classification(output_folder+'tokens-file.jl',
                embeddings_file, output_folder+'pos-neg-train.txt',
                ContextVectorGenerators.ContextVectorGenerators.symmetric_generator,
                text_attribute, annotated_attribute, correct_attribute)

def data_preparation_for_actual_data(actual_file, embeddings_file, text_attribute, annotated_attribute, output_folder, correct_attribute):
    """
    At present, this script cannot deal with multi-token annotations (e.g. 'Mary Ann' or 'Salt lake city'). We
    will convert all tokens to lower-case; thus, case-differences will not be accounted for.

    Two files will be written out to the output_folder, one of which will be intermediate, and the other of which
    is the file on which we will train/test the machine learning model.
    :param jlines_file: A file where each line is a json.
    :param embeddings_file: At present, use the provided file; do not try to generate it yourself
    :param text_attribute: e.g. 'high_recall_readability_text'
    :param annotated_attribute: e.g. 'annotated_cities'
    :param output_folder: a folder for writing out files in
    :return: None
    """
    print ">>Data Preparation for Actual Data<<"
    TextPreprocessors.TextPreprocessors.preprocess_annotated_file(actual_file, text_attribute,
                                                                  output_folder+'tokens-file.jl')
    TokenSupervised.TokenSupervised.prep_preprocessed_actual_file_for_classification(output_folder+'tokens-file.jl',
                embeddings_file, output_folder+'pos-neg-actual.txt',
                ContextVectorGenerators.ContextVectorGenerators.symmetric_generator,
                text_attribute, annotated_attribute, correct_attribute)


def post_processing(classified_cities, actual_data_file):
    TextPreprocessors.TextPreprocessors.post_processing(classified_cities, actual_data_file, type=TYPE)
                    
def classification_script(pos_neg_file_training, pos_neg_file_actual_data, GENERATE):
    """
    Run this code after running a data preparation script.
    Prints out a bunch of metrics.
    :param pos_neg_file: This is the pos-neg-file.txt generated by data preparation in the output folder.
    :return: None
    """
    print ">>Classification Script<<"
    #TokenSupervised.TokenSupervised.trial_script_binary(pos_neg_file_training)
    model = TokenSupervised.TokenSupervised.extract_model(pos_neg_file_training)
    persist(model)
    if(GENERATE == 1):
        return None

    model['model'] = joblib.load('model.pkl')
    return TokenSupervised.TokenSupervised.classify_data(model, pos_neg_file_actual_data)

def persist(classifier):
    if('scaler' in classifier):
        joblib.dump(classifier['scaler'], 'scaler.pkl')
        
    if('normalizer' in classifier):
        joblib.dump(classifier['normalizer'], 'normalizer.pkl')

    if('k_best' in classifier):
        joblib.dump(classifier['k_best'], 'k_best.pkl')

    print ">>Dumping Model File:", TYPE+".pkl<<"
    joblib.dump(classifier['model'], TYPE+'.pkl', compress=1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Arguments Missing- <TYPE - one of cities, ethnicity, name, eye-color, hair-color> [<ONLY_GENERATE - 1(default) or 0 >]")
        exit()

    # Take Input Arguments
    TYPE = sys.argv[1]
    TRAINING_FILE = 'manual_100_'+TYPE+'.jl'
    ACTUAL_FILE = 'manual_100_'+TYPE+'.jl'

    if len(sys.argv) == 3:
        GENERATE = int(sys.argv[2])

    print "Running for ",TYPE
    print "Only Generate Model File", GENERATE

    path = os.path.dirname(os.path.abspath(__file__)) + '/'+DATA_FOLDER+'/'
    data_preparation_for_training_data(path+TRAINING_FILE, path+UNIGRAM_FILE,'readability_text', 'annotated_'+TYPE, 'correct_'+TYPE, path+'output_folder/')

    if(GENERATE != 1):
        data_preparation_for_actual_data(path+ACTUAL_FILE, path+UNIGRAM_FILE,'readability_text', 'annotated_'+TYPE, path+'output_folder/', 'correct_'+TYPE)

    classified_cities = classification_script(path+'output_folder/pos-neg-train.txt', path+'output_folder/pos-neg-actual.txt', GENERATE)
    
    if(GENERATE != 1):
        post_processing(classified_cities, path+ACTUAL_FILE)