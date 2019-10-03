#!/usr/bin/env python3
'''
pre process raw sentences, save them in a file, and pass it to
the parser.

- at most 5 ==> no
- at least 10 ==> some
- a few ==> several

input: tokenized text
output: tokenized text and a logfile

'''

__author__ = "Hai Hu"
__email__ = "huhai@indiana.edu"

import sys, os, re, copy, argparse
from getMono import eprint
from pass2act import pass2act
import spacy, utils
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

def main():
    # fn = "test.tok"
    fn = sys.argv[1]
    preprocess(fn)

def preprocess(fn):
    """ produce a clean file named: test.tok.clean
    and log file: test.tok.preprocess.log """
    sent_id = -1
    fh_log = open(fn + '.preprocess.log', 'w')
    fh_log.write("sentId,before,after,idx\n")
    fh_clean = open(fn + '.clean', 'w')
    s_pattern = "{},{},{},{}\n"
    nlp = spacy.load('en')
    # p2a = P2A_transformer(spacy.load('en'))
    # corenlp = StanfordCoreNLP('http://localhost', port=9000, lang='en')
    corenlp = None

    eprint('\npreprocessing...')
    with open(fn) as f:
        for line in f:
            line = line.strip()
            if line == "": continue

            sent_id += 1
            # print('\npreprocessing:', sent_id)

            # line = line.lower()

            eprint('\nbefore :', line)
            line = preprocess_line(line, fh_log, s_pattern, sent_id, corenlp)
            eprint('after :', line)

            # write to clean file
            fh_clean.write(line)
            fh_clean.write('\n')

    fh_log.close()
    fh_clean.close()
    eprint('...done!\n')

def preprocess_line(line, fh_log, s_pattern, sent_id, corenlp):
    """ preprocess one line """
    line_lower = line.lower()

    # ----------------------------------------------
    # for now, only 1 `at most/least' allowed in line
    if 'at most' in line_lower:
        line = subst(line, 'most', fh_log, s_pattern, sent_id)
    if 'at least' in line_lower:
        line = subst(line, 'least', fh_log, s_pattern, sent_id)
    if 'a few' in line_lower:
        line = pat['a_few'].sub('several', line)
        # no need to write to log, just use 'several'

    # ----------------------------------------------
    # green/blue ... colored -> green/blue
    # line = line.replace("blue colored", "blue").replace("green colored", "green").\
    #     replace("brown colored", "brown").replace("dark colored", "dark").\
    #     replace("light colored", "light").replace("orange colored", "orange").\
    #     replace("purple colored", "purple")

    # ----------------------------------------------
    # a group of -> some
    # line = line.replace("A group of four", "Four").replace("A group of five", "Five")
    # line = line.replace("A cluster of four", "Four")
    # line = line.replace("A group of", "Some").replace("a group of", "some")

    # ----------------------------------------------
    # fix ``a lot of''
    if "a lot of " in line_lower:
        line = fix_a_lot_of(line, fh_log, s_pattern, sent_id)

    # ----------------------------------------------
    # someone/body -> some person; nobody/no one -> no person
    line = PAT_someone.sub("some person", line)
    line = PAT_noone.sub("no person", line)
    line = PAT_everyone.sub("every person", line)

    # ----------------------------------------------
    # n't -> not
    line = line.replace(" n't ", " not ")

    # ----------------------------------------------
    # the -> a
    # line = line.replace("The ", "A ").replace(" the ", " a ")

    # ----------------------------------------------
    # there is no ... -> no boy/woman/person ...
    # if PAT_there_be_no.match(line):
    #     new_sent, new_sent2, diff = utils.there_be_no_sent(line, corenlp)
    #     line = new_sent2
    # else:  # TODO only pass2act if not "there be no"

    # ----------------------------------------------
    # pass2act
    if any([p in line for p in PASS_PATTERN]):
        if " by " not in line:
            line += " by a thing"
        line_old = line[:]
        line = pass2act(line).strip('. ')
        if line == line_old and line.endswith(" by a thing"):
            line = line[:-11]  # remove by a thing if still not activized

    # ----------------------------------------------
    # numbers
    line = line.replace('Two ', '2 ').replace(' two ', ' 2 ')
    line = line.replace('Three ', '3 ').replace(' three ', ' 3 ')
    line = line.replace('Four ', '4 ').replace(' four ', ' 4 ')
    line = line.replace('Five ', '5 ').replace(' five ', ' 5 ')

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
        if word.lower() == 'at' and line_list[idx + 1].lower() == quantifier:  # 'most':
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
    fh_log.write(s_pattern.format(str(sent_id), original, after, str(idx_at)))

    return line

def fix_a_lot_of(line, fh_log, s_pattern, sent_id):
    """ change 'a lot of' to 'much' """
    # log
    fh_log.write(s_pattern.format(str(sent_id), "a-lot-of", "much", str(-1)))
    return line.replace('a lot of', 'much').replace('A lot of', 'Much')

if __name__ == '__main__':
    main()









