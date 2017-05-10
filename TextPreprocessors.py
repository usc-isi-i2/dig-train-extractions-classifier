import codecs
import json
from nltk.tokenize import sent_tokenize, word_tokenize
import re
import nltk
from scipy.stats import rankdata
import numpy as np
import random

from digExtractor.extractor import Extractor
from digExtractor.extractor_processor import ExtractorProcessor
from digTokenizerExtractor.tokenizer_extractor import TokenizerExtractor



class TextPreprocessors:
    """
    Contains static methods for taking the json objects and pre-processing/condensing text fields in them
    so they are more suitable for word-embedding code.
    """

    @staticmethod
    def is_sublist_in_big_list(big_list, sublist):
        # matches = []
        for i in range(len(big_list)):
            if big_list[i] == sublist[0] and big_list[i:i + len(sublist)] == sublist:
                return True
        return False

    @staticmethod
    def tokenize_string(string):
        """
        I designed this method to be used independently of an obj/field. If this is the case, call _tokenize_field.
        It's more robust.
        :param string: e.g. 'salt lake city'
        :return: list of tokens
        """
        list_of_sentences = list()
        tmp = list()
        tmp.append(string)
        k = list()
        k.append(tmp)
        # print k
        list_of_sentences += k  # we are assuming this is a unicode/string

        word_tokens = list()
        for sentences in list_of_sentences:
            # print sentences
            for sentence in sentences:
                for s in sent_tokenize(sentence):
                    word_tokens += word_tokenize(s)

        return word_tokens

    @staticmethod
    def _tokenize_field(obj, field, method='dig'):
        """
        At present, we'll deal with only one field (e.g. readability_text). The field could be a unicode
        or a list, so make sure to take both into account.

        We are not preprocessing the tokens in any way. For this, I'll write another function.
        :param obj: the adultservice json object
        :param field: e.g. 'readability_text'
        :return: A list of tokens.
        """

        word_tokens = list()

        if(method == 'nltk'):
            list_of_sentences = list()

            if field not in obj:
                return None
            elif type(obj[field]) == list:
                k = list()
                k.append(obj[field])
                list_of_sentences += k
            else:
                tmp = list()
                tmp.append(obj[field])
                k = list()
                k.append(tmp)
                # print k
                list_of_sentences += k  # we are assuming this is a unicode/string
            for sentences in list_of_sentences:
                # print sentences
                for sentence in sentences:
                    for s in sent_tokenize(sentence):
                        word_tokens += word_tokenize(s)

        elif(method == 'dig'):
            doc = { 'string': obj[field]}
            e = TokenizerExtractor()
            ep = ExtractorProcessor().set_input_fields('string').set_output_field('output').set_extractor(e)
            updated_doc = ep.extract(doc)
            word_tokens = updated_doc['output'][0]['result'][0]['value']

        return word_tokens

    @staticmethod
    def _preprocess_tokens(tokens_list, options=['remove_non_alpha','lower']):
        """

        :param tokens_list: The list generated by tokenize_field per object
        :param options: A list of to-dos.
        :return: A list of processed tokens. The original list is unmodified.
        """
        new_list = list(tokens_list)
        for option in options:
            if option == 'remove_non_alpha':
                tmp_list = list()
                for token in new_list:
                    if token.isalpha():
                        tmp_list.append(token)
                del new_list
                new_list = tmp_list
            elif option == 'lower':
                for i in range(0, len(new_list)):
                    new_list[i] = new_list[i].lower()
            else:
                print 'Warning. Option not recognized: '+option

        return new_list

    @staticmethod
    def _preprocess_sampled_annotated_file(sample_file, output_file):
        """
        We sampled files in FieldAnalyses.sample_n_values_from_field, and then labeled them. The problem is
        that we sampled raw values, and now I've done too much labeling to rectify. This is a one-time piece of
         code for the two files we have already sampled/labeled.
        :param sample_file:
        :return:
        """
        out = codecs.open(output_file, 'w', 'utf-8')
        with codecs.open(sample_file, 'r', 'utf-8') as f:
            for line in f:
                fields = re.split('\t',line)
                word_tokens = list()
                for s in sent_tokenize(fields[0]):
                    word_tokens += word_tokenize(s)
                fields[0] = ' '.join(word_tokens)
                out.write('\t'.join(fields))
        out.close()

    @staticmethod
    def _extract_name_strings_from_dict_lists(obj, field='telephone', return_as_tokens = False):
        """
        We're assuming that obj contains 'field' (make sure to have checked for this) which is a list
        containing dicts. Each dict contains a name field. We will return a string of phone numbers in
        alphabetic order.
        :param obj:
        :param field: e.g. telephone or email
        :param return_as_tokens: if True we will return a list, otherwise we'll join and return as string.
        :return: A string, (sorted) list of unique tokens or None (if no names exist within the list)
        """
        phones = set()
        for phone in obj[field]:
            if 'name' in phone and phone['name']:
                if type(phone['name']) == list:
                    phones = phones.union(set(phone['name']))
                else:
                    phones.add(phone['name'])
        if not phones:
            return None
        else:
            phones = list(phones)
            phones.sort()
            if return_as_tokens:
                return phones
            else:
                return '-'.join(phones)

    @staticmethod
    def build_tokens_objects_from_readability(input_file, output_file):
        """

        :param input_file: A json lines file
        :param output_file: A tokens file
        :return: None
        """
        field = 'readability_text'
        out = codecs.open(output_file, 'w', 'utf-8')
        with codecs.open(input_file, 'r', 'utf-8') as f:
            for line in f:
                tokens_obj = dict()
                obj = json.loads(line)
                tokenized_field = TextPreprocessors._tokenize_field(obj, field)
                if tokenized_field:
                    tokens_obj[obj['identifier']] = TextPreprocessors._preprocess_tokens(tokenized_field, options=["lower"])
                    json.dump(tokens_obj, out)
                    out.write('\n')
        out.close()

    @staticmethod
    def build_phone_objects_from_all_fields(input_file, output_file, exclude_fields = None, exclude_field_regex = None):
        """
        Be careful about the assumptions for the field structure. This function is not going to be appropriate for
        every jlines file.
        :param input_file: A json lines file
        :param output_file: A tokens file, where an identifier has two fields: tokens and phone. Both are lists. Be
        careful about usage; we will use this file primarily for generating phone embeddings.
        :param exclude_fields: If the field is within this list, we will ignore that field.
        :param exclude_field_regex: a regex string, where, if the field name matches this regex, we ignore it.
        :return: None
        """
        # field = 'readability_text'
        out = codecs.open(output_file, 'w', 'utf-8')
        with codecs.open(input_file, 'r', 'utf-8') as f:
            for line in f:
                obj = json.loads(line)

                # get phone string, if one exists
                if 'telephone' not in obj:
                    continue
                else:
                    phone = TextPreprocessors._extract_name_strings_from_dict_lists(obj)
                    if not phone:
                        continue

                # get tokens list, if one exists
                tokens_list = []
                for k in obj.keys():
                    if k == 'telephone':
                        continue
                    if exclude_fields:
                        if k in exclude_fields:
                            continue
                    if exclude_field_regex:
                        pat = re.split(exclude_field_regex, k)
                        print pat
                        if not (pat and len(pat) == 1 and pat[0] == k):
                            continue
                    # print k
                    if k == 'email':
                        tokenized_field = TextPreprocessors._extract_name_strings_from_dict_lists(obj, 'email', True)
                    else:
                        tokenized_field = TextPreprocessors._tokenize_field(obj, k)
                    if tokenized_field:
                        tokens = TextPreprocessors._preprocess_tokens(tokenized_field, options=["lower"])
                        if tokens:
                            tokens_list += tokens

                if not tokens_list:
                    continue

                # assuming we made it this far, we have everything we need
                inner_obj = dict()
                inner_obj['phone'] = phone
                inner_obj['tokens_list'] = tokens_list
                tokens_obj = dict()
                tokens_obj[obj['identifier']] = inner_obj
                json.dump(tokens_obj, out)
                out.write('\n')
        out.close()

    @staticmethod
    def convert_txt_dict_to_json(input_file, output_file):
        results = list()
        with codecs.open(input_file, 'r', 'utf-8') as f:
            for line in f:
                results.append(line[0:-1])
        out = codecs.open(output_file, 'w', 'utf-8')
        json.dump(results, out, indent=4)
        out.close()

    @staticmethod
    def preprocess_annotated_cities_file(input_file, output_file):
        """
        We will take in a file such as annotated-cities-1.json as input and output another json that:
        tokenizes the high_recall_readability_text field and converts it to lower-case.
        converts values in the other two fields to lowercase

        These preprocessed files can then be used for analysis.

        Note that the field names remain the same in the output file, even though high_recall-* is now
         a list of tokens instead of a string.
        :param input_file:
        :param output_file:
        :return:
        """
        out = codecs.open(output_file, 'w', 'utf-8')
        with codecs.open(input_file, 'r', 'utf-8') as f:
            for line in f:
                obj = json.loads(line)
                tokenized_field = TextPreprocessors._tokenize_field(obj, 'high_recall_readability_text')
                if tokenized_field:
                    obj['high_recall_readability_text'] = TextPreprocessors._preprocess_tokens(tokenized_field, options=["lower"])
                    for k in obj.keys():
                        obj[k] = TextPreprocessors._preprocess_tokens(obj[k], options=["lower"])
                    json.dump(obj, out)
                    out.write('\n')
        out.close()

    @staticmethod
    def preprocess_annotated_file(input_file, text_field, output_file):
        """
        We will take in a file such as annotated-cities-1.json as input and output another json that:
        tokenizes the text( e.g. high_recall_readability_text field) and converts it to lower-case.
        converts values in all other fields to lowercase

        These preprocessed files can then be used for analysis.

        Note that the field names remain the same in the output file, even though high_recall-* is now
         a list of tokens instead of a string.
        :param input_file:
        :param text_field:
        :param output_file:
        :return:
        """
        out = codecs.open(output_file, 'w', 'utf-8')
        with codecs.open(input_file, 'r', 'utf-8') as f:
            for line in f:
                obj = json.loads(line)
                tokenized_field = TextPreprocessors._tokenize_field(obj, text_field)
                if tokenized_field:
                    obj[text_field] = TextPreprocessors._preprocess_tokens(tokenized_field,
                                                                                               options=["lower"])
                    for k in obj.keys():
                        obj[k] = TextPreprocessors._preprocess_tokens(obj[k], options=["lower"])
                    json.dump(obj, out)
                    out.write('\n')
        out.close()

    @staticmethod
    def get_rankings(data):
        return rankdata(data, method='dense')

    @staticmethod
    def get_reverse_ranking(labels, rankings):
        min_rank_of_correct_city = len(labels)
        max_rank_of_correct_city = 1
        atleast_one_correct = False
        for city_index, label in enumerate(labels):
            if(label == 1):
                #It is a correct city
                atleast_one_correct = True
                if(rankings[city_index] < min_rank_of_correct_city):
                    min_rank_of_correct_city = rankings[city_index]

                if(rankings[city_index] > max_rank_of_correct_city):
                    max_rank_of_correct_city = rankings[city_index]

        if(not atleast_one_correct):
            #No correct cities. Cannot define min and max rank
            return None

        #print "Min Rank:",
        #print min_rank_of_correct_city
        #print "Max Rank:",
        #print max_rank_of_correct_city

        reverse_min_rank = 1/min_rank_of_correct_city
        reverse_max_rank = 1/max_rank_of_correct_city
                
        return {'min':reverse_min_rank, 'max':reverse_max_rank}


    @staticmethod
    def post_processing(classified_cities, actual_data_file, ranking = True, type = 'cities'):
        combined_all_data = classified_cities['combined_all_data']

        if(ranking):
            reverse_min_ranks = []
            reverse_max_ranks = []
            random_reverse_min_ranks = []
            random_reverse_max_ranks = []
            for data_obj in combined_all_data:
                city_names = data_obj['combined_city_name']

                if(len(city_names) == 0):
                    continue

                negative_class_prob = data_obj['combined_city_negative_prob']
                actual_labels = data_obj['combined_city_actual_label']
                rankings = TextPreprocessors.get_rankings(negative_class_prob)
                random_rankings = range(1,len(actual_labels)+1) 
                random.shuffle(random_rankings)

                print "Attribute Names:",
                print city_names
                print "Labels:",
                print actual_labels
                print "Rankings:",
                print rankings

                reverse_ranks = TextPreprocessors.get_reverse_ranking(actual_labels, rankings)

                if(reverse_ranks is not None):
                    reverse_max_ranks.append(reverse_ranks['max'])
                    reverse_min_ranks.append(reverse_ranks['min'])

                    random_reverse_ranks = TextPreprocessors.get_reverse_ranking(actual_labels, random_rankings)
                    random_reverse_max_ranks.append(random_reverse_ranks['max'])
            
                    random_reverse_min_ranks.append(random_reverse_ranks['min'])


            print "MRR (Max Ranks):",
            print np.mean(reverse_max_ranks)
            print "MRR (Min Ranks):",
            print np.mean(reverse_min_ranks)

            print "Random MRR (Max Ranks):",
            print np.mean(random_reverse_max_ranks)
            print "Random MRR (Min Ranks):",
            print np.mean(random_reverse_min_ranks)










        classified_cities = classified_cities['classified_cities']
        print "Length:"+str(len(classified_cities))
        print "{}: {}, {}, {}, {}".format("Index:", "classified_city_which_is_a_city",
            "classified_city_which_is_not_a_city", "city_not_classified_as_city", 
            "total_correct_cities")
        total_correct_cities = 0
        total_classified_city_which_is_a_city = 0
        total_classified_city_which_is_not_a_city = 0
        total_city_not_classified_as_city = 0
        with codecs.open(actual_data_file, 'r', 'utf-8') as f:
            print len(classified_cities)
            print classified_cities
            for index, line in enumerate(f):
                print index
                obj = json.loads(line)
                correct_cities = set(obj['correct_'+type])
                annotated_cities = set(obj['annotated_'+type])
                classified_as_cities = classified_cities[index]['cities']
                classified_as_borderline = classified_cities[index]['borderline_cities']
                classified_as_cities = classified_as_cities | classified_as_borderline
                classified_as_not_cities = classified_cities[index]['not_cities']
                total_annotated_cities = len(classified_as_cities) + len(classified_as_borderline) + len(classified_as_not_cities)
                total_cities_provided = len(annotated_cities)
                classified_city_which_is_a_city = list()
                classified_city_which_is_not_a_city = list()
                city_not_classified_as_city = list()
                for city in classified_as_cities:
                    if(city in correct_cities):
                        classified_city_which_is_a_city.append(city)
                    else:
                        classified_city_which_is_not_a_city.append(city)
                for city in correct_cities:
                    if(city not in classified_as_cities):
                        city_not_classified_as_city.append(city)
                print "{}: {}, {}, {}, {}".format(index, len(classified_city_which_is_a_city), 
                    len(classified_city_which_is_not_a_city), len(city_not_classified_as_city), len(correct_cities))
                total_correct_cities += len(correct_cities)
                total_classified_city_which_is_a_city += len(classified_city_which_is_a_city)
                total_classified_city_which_is_not_a_city += len(classified_city_which_is_not_a_city)
                total_city_not_classified_as_city += len(city_not_classified_as_city)
                #print total_annotated_cities
                #print total_cities_provided
                #print classified_city_which_is_a_city
                #print classified_city_which_is_not_a_city
                #print city_not_classified_as_city

        print "{}: {}, {}, {}, {}\n".format("Total:", total_classified_city_which_is_a_city,
            total_classified_city_which_is_not_a_city, total_city_not_classified_as_city, 
            total_correct_cities)

        print "Precision: {}".format(float(total_classified_city_which_is_a_city)/(total_classified_city_which_is_a_city+total_classified_city_which_is_not_a_city))
        print "Recall: {}".format(float(total_classified_city_which_is_a_city)/(total_classified_city_which_is_a_city+total_city_not_classified_as_city))

                
# path='/Users/mayankkejriwal/ubuntu-vm-stuff/home/mayankkejriwal/tmp/'
# TextPreprocessors.preprocess_annotated_cities_file(path+'raw-data/annotated-cities-2.json',
#                                                 path+'prepped-data/annotated-cities-2-prepped.json')
# TextPreprocessors.convert_txt_dict_to_json(path+'dictionaries/spa-massage-words.txt', path+'dictionaries/spa-massage-words.json')
# TextPreprocessors.build_tokens_objects_from_readability(path+'part-00000.json',
# path+'readability_tokens-part-00000-onlyLower.json')
# exclude_fields_1 = ['high_recall_readability_text', 'identifier', 'inferlink_text', 'readability_text', 'seller']
# exclude_field_regex = '\.*_count'
# string = 'readability_text'
# print re.split(exclude_field_regex, string)
# print '-'.join(exclude_fields_1)
# TextPreprocessors.build_phone_objects_from_all_fields(path+'part-00000.json',
# path+'all_tokens-part-00000-onlyLower-1.json', exclude_fields_1, exclude_field_regex)
# print TextPreprocessors.tokenize_string('salt')
