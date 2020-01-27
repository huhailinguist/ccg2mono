#!/usr/bin/env python3
'''
pre process raw sentences, save them in a file, and pass it to
the parser.

- at most 5 ==> no
- at least 10 ==> some
- a few ==> several

input: tokenized text
output: 
1. tokenized text (test.tok.clean) 
2. a logfile (test.tok.preprocess.log)

'''

__author__ = "Hai Hu"
__email__ = "huhai@indiana.edu"

import sys, os, re, copy, argparse
# import utils
from getMono import eprint
# from pass2act import P2A_transformer
# import spacy
# from stanfordcorenlp import StanfordCoreNLP

pat = { 'most' : re.compile("[Aa]t most \d+"),
        'least': re.compile("[Aa]t least \d+"),
        'a_few': re.compile("[Aa] few")}

PASS_PATTERN = {" are being ", " is being ", " am being ", " were being ",
                " was being ", " be being ", " have been being",
                " has been being ", " had been being "}

PAT_someone = re.compile("[Ss]ome(one|body)")
PAT_noone = re.compile("[Nn]o(body| one)")
PAT_everyone = re.compile("[Ee]very(one|body)")
PAT_there_be_no = re.compile("[Tt]here (is|are) no")

PAT_something = re.compile("[Ss]omething")
PAT_nothing = re.compile("[Nn]othing")
PAT_everything = re.compile("[Ee]verything")
PAT_somewhere = re.compile("[Ss]omewhere")
PAT_nowhere = re.compile("[Nn]owhere")
PAT_everywhere = re.compile("[Ee]verywhere")

PAT_more_than_n = re.compile("[Mm]ore than (\d+)")
PAT_less_than_n = re.compile("[Ll]ess than (\d+)")
PAT_at_most_n = re.compile("[Aa]t most (\d+)")
PAT_at_least_n = re.compile("[Aa]t least (\d+)")
PAT_exactly_n = re.compile("[Ee]xactly (\d+)")
PAT_some_but_not_all = re.compile("[Ss]ome but not all")

QUANTIFIERS = {
    "some", "no", "every", "all", "each",
    # "exactly",
    "most", 
    # "many",
    "several", "few",
    # "more than", "less than", "at least", "at most",
    "some-but-not-all"
}

def main():
    # fn = "test.tok"
    fn = sys.argv[1]
    preprocess(fn)

def preprocess(fn):
    """ produce a clean file named: test.tok.clean
    and log file: test.tok.preprocess.log """
    sent_id = -1
    fh_log = open(fn + '.preprocess.log', 'w')
    fh_log.write("sentId,before,after,idx,len_sent\n")
    fh_clean = open(fn + '.clean', 'w')
    s_pattern = "{},{},{},{},{}\n"
    # p2a = P2A_transformer(spacy.load('en'))
    # corenlp = StanfordCoreNLP('http://localhost', port=9000, lang='en')

    eprint('\npreprocessing...')
    with open(fn) as f:
        for line in f:
            line = line.strip()
            if line == "": continue

            sent_id += 1
            # print('\npreprocessing:', sent_id)

            # line = line.lower()

            eprint('\nbefore:', line)

            # with passitve to active transformation
            # line = preprocess_line(line, fh_log, s_pattern, sent_id, p2a, corenlp)

            # no passive to active transformation
            line = preprocess_line(line, fh_log, s_pattern, sent_id)
            eprint('after :', line)

            # write to clean file
            fh_clean.write(line)
            fh_clean.write('\n')

    fh_log.close()
    fh_clean.close()
    eprint('...done!\n')

def preprocess_line(line, fh_log, s_pattern, sent_id, p2a=None, corenlp=None):
    """ preprocess one line """
    line_lower = line.lower()

    # ----------------------------------------------
    # change `#` to `number`
    # e.g.: # 6 tries her best to help her team to victory
    line = line.replace("#", "number")

    # ----------------------------------------------
    # green/blue ... colored -> green/blue
    #line = line.replace("blue colored", "blue").replace("green colored", "green").\
    #    replace("brown colored", "brown").replace("dark colored", "dark").\
    #    replace("light colored", "light").replace("orange colored", "orange").\
    #    replace("purple colored", "purple")

    # ----------------------------------------------
    # a group of -> some
    line = line.replace("A group of four", "Four").replace("A group of five", "Five")
    line = line.replace("A cluster of four", "Four")
    line = line.replace("A group of", "Some").replace("a group of", "some")

    # ----------------------------------------------
    # fix ``a lot of''
    if "a lot of " in line_lower:
        line = fix_a_lot_of(line, fh_log, s_pattern, sent_id)

    # ----------------------------------------------
    # someone/body -> some person; nobody/no one -> no person
    line = PAT_someone.sub("some person", line)
    line = PAT_noone.sub("no person", line)
    line = PAT_everyone.sub("every person", line)

    line = PAT_something.sub("some thing", line)
    line = PAT_nothing.sub("no thing", line)
    line = PAT_everything.sub("every thing", line)

    line = PAT_somewhere.sub("some place", line)
    line = PAT_nowhere.sub("no place", line)
    line = PAT_everywhere.sub("every place", line)

    # ----------------------------------------------
    # n't -> not
    line = line.replace(" n't ", " not ")

    # ----------------------------------------------
    # the -> a
    # line = line.replace("The ", "A ").replace(" the ", " a ")

    # ----------------------------------------------
    # there is no ... -> no boy/woman/person ...
    #if PAT_there_be_no.match(line):
    #    new_sent, new_sent2, diff = utils.there_be_no_sent(line, corenlp)
    #    line = new_sent2
    # else:  pass # TODO only pass2act if not "there be no"

    # ----------------------------------------------
    # pass2actPAT_a_few
    #    line_old = line[:]
    #    line = p2a.pass2act(line).strip('. ')
    #    if line == line_old and line.endswith(" by a thing"):
    #        line = line[:-11]  # remove by a thing if still not activized

    # ----------------------------------------------
    # numbers
    line = line.replace('Two ', '2 ').replace(' two ', ' 2 ')
    line = line.replace('Three ', '3 ').replace(' three ', ' 3 ')
    line = line.replace('Four ', '4 ').replace(' four ', ' 4 ')
    line = line.replace('Five ', '5 ').replace(' five ', ' 5 ')
    line = line.replace('Six ', '6 ').replace(' six ', ' 6 ')
    line = line.replace('Seven ', '7 ').replace(' seven ', ' 7 ')
    line = line.replace('Eight ', '8 ').replace(' eight ', ' 8 ')
    line = line.replace('Nine ', '9 ').replace(' nine ', ' 9 ')

    # ----------------------------------------------
    if 'a few' in line_lower:
        line = pat['a_few'].sub('several', line)
        # no need to write to log, just use 'several'

    # ----------------------------------------------
    # fix quantifiers

    line = PAT_more_than_n.sub("more-than-\\1", line)
    line = PAT_less_than_n.sub("less-than-\\1", line)
    line = PAT_at_least_n.sub("at-least-\\1", line)
    line = PAT_at_most_n.sub("at-most-\\1", line)
    line = PAT_exactly_n.sub("exactly-\\1", line)
    line = PAT_some_but_not_all.sub("some-but-not-all", line)

    quant_cnt = 0
    new_line = []
    len_sent = len(line.split())
    for idx, word in enumerate(line.split()):
        if word.lower() in QUANTIFIERS:
            quant_cnt += 1
            new_line.append(word)
        # more than n, at least n -> some
        elif word.lower().startswith("more-than-") or word.lower().startswith("at-least-"):
            new_line.append("some")
            # write to log
            fh_log.write(s_pattern.format(str(sent_id), word, "some", str(idx), len_sent))
        # less than n, at most n -> no
        elif word.lower().startswith("less-than-") or word.lower().startswith("at-most-"):
            new_line.append("no")
            # write to log
            fh_log.write(s_pattern.format(str(sent_id), word, "no", str(idx), len_sent))
        # exactly n -> some
        elif word.lower().startswith("exactly-"):
            new_line.append("some")
            fh_log.write(s_pattern.format(str(sent_id), word, "some", str(idx), len_sent))
        # many -> most
        # elif word.lower().startswith("many"):
        #     new_line.append("every")
        #     fh_log.write(s_pattern.format(str(sent_id), word, "every", str(idx), len_sent))
        else:
            new_line.append(word)

    line = " ".join(new_line)

    # make sure first letter is capital
    line = line[0].upper() + line[1:]

    return line

def subst(line, quantifier, fh_log, s_pattern, sent_id, verbose=False):
    """ substitute: word = most/least """
    # find the index of `at' in line.split()
    idx_at = -1
    line_list = line.split()
    num_tokens = len(line_list)
    for idx, word in enumerate(line_list):
        if idx == num_tokens - 2: break
        if word.lower() == 'at' and \
                line_list[idx + 1].lower() == quantifier:  # 'most':
            idx_at = idx
            break

    # replace `at most 10' with `no'
    m = pat[quantifier].search(line)
    if m: original = m.group(0)
    else: return line
    eprint('original:', original)
    if quantifier == 'most': after = "no"
    elif quantifier == 'least': after = "some"
    line = pat[quantifier].sub(after, line)

    # log
    fh_log.write(s_pattern.format(str(sent_id), original, after, str(idx_at), len(line_list)))

    return line

def fix_a_lot_of(line, fh_log, s_pattern, sent_id):
    """ change 'a lot of' to 'much' """
    # log
    fh_log.write(s_pattern.format(str(sent_id), "a-lot-of", "much", "-1", len(line.split())))
    return line.replace('a lot of', 'much').replace('A lot of', 'Much')

if __name__ == '__main__':
    main()









