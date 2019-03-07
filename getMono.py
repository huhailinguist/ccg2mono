#!/usr/bin/env python3
'''
parse candc/easyccg xml and polarize

PIPELINE:
1. read in C&C output.xml, parse the trees into out data structure

2. For each tree:
  - mark: assign plus and minus signs to each node
    a. mark leafNodes
    b. mark nonTermNodes

  - polarize

3. output to xml/html format

Hai Hu, Feb, 2018
'''

import sys, os, re, copy, argparse
from sys import exit
from bs4 import BeautifulSoup
# from IPython.display import Markdown, display

# uparrow: U+2191, down arrow: U+2193

__author__ = "Hai Hu; Larry Moss"
__email__ = "huhai@indiana.edu; lmoss@indiana.edu"

# define different types of implicatives. Did not include ones with *
# from http://web.stanford.edu/group/csli_lnr/Lexical_Resources/simple-implicatives/simple-implicatives.txt
# pp|nn
IMP_pp_nn = {"allow","bear","begin","bother","come","condescend","dare",
"deign","enable","get","go","grow","have","know","let","live","manage",
"remember","serve","start","stay","trouble","turn","use","wake"}

# pp
IMP_pp = {"admit","arrange","bring","cause","confirm","demonstrate","discover",
"drive","ensure","force","grant","hasten","help","jump","lead","make","observe",
"provoke","reveal","rope","show","tend","use","verify"}

# nn
IMP_nn = {"attempt","compete","permit","qualify","think"}

# pn|np
IMP_pn_np = {"fail","forget","neglect","refrain"}

# pn
IMP_pn = {"decline","refuse","remain"}

# np
IMP_np = {"explain","guess","hesitate","mean","predict",
          "specify","suspect"}

# neutral: want to, from Nairn 2006
IMP_px_nx = {"want"}

QUANTIFIERS_TO_FIX = {'MOST', 'MANY', 'FEW', 'SEVERAL', 'ONE', '2', '3', '4', '5'}

# TODO for all semCat, make everything + except NP, N, PP, PR, S
EXCLUDE = {"((e,t),t)", "(e,t)", "t", "pp", "pr"}

# downward entailing prepositions
DE_PREP = {'OUTSIDE', 'WITHOUT', 'OUT', 'EXCEPT'}

RC_PRON = {'WHO', 'WHICH', 'THAT'}


def main():
    # -------------------------------------
    # parse cmd arguments
    description = """
    Polarize CCG trees. Authors: Hai Hu, Larry Moss
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-s', '--sentNo', dest='sentNo', type=str, nargs='+', default=['all'],
                        help='index(s) of sentence to process. E.g. "2", "3 5", "all" '
                             "[default: %(default)s]")
    parser.add_argument('-p', dest='parser', default='candc', choices=['candc', 'easyccg'],
                        help='parser of your choice: candc, easyccg '
                             "[default: %(default)s]")
    parser.add_argument('-v', dest='verbose', choices=[-1,0,1,2,3,4], type=int, default=-1,
                        help='verbose: -1: None, 0: after reading in tree, '
                             '1: after fixTree(), '
                             '2: after mark(), 3: after polarize(), \n4: all '
                             "[default: %(default)s]")
    parser.add_argument('-f', dest='filename', type=str, default='tmp.candc.parsed.xml',
                        help='parser output filename. E.g. fracas_1_80.raw.easyccg.parsed.txt, or '
                             'tmp.candc.parsed.xml '
                             "[default: %(default)s]")
    parser.add_argument('-flog', dest='filename_log', type=str, default='',
                        help='preprocess log filename. E.g. test.tok.preprocess.log'
                             "[default: %(default)s]")
    parser.add_argument('-t', dest='test', action='store_const', const=True, default=False,
                        help='if -t, run test()')
    args = parser.parse_args()
    # -------------------------------------

    if args.test:
        print('in test')
        test()
        exit()

    eprint("trees to build: ", args.sentNo)
    if args.sentNo == ['all']:
        args.sentNo = []
    else:
        args.sentNo = [int(i) for i in args.sentNo]

    # intialize trees
    try:
        trees = CCGtrees(args.filename_log)
    except FileNotFoundError:
        eprint('please specify filename of pre process log, using -flog')
        exit()

    # parser output filename
    if os.path.isfile(args.filename):
        if '.candc.' in args.filename:
            args.parser = 'candc'
            trees.readCandCxml(args.filename, args.sentNo)
        else:
            args.parser = 'easyccg'
            trees.readEasyccgStr(args.filename, args.sentNo)
    else:
        try:
            if args.parser == 'candc':
                trees.readCandCxml('tmp.candc.parsed.xml')
            else: trees.readEasyccgStr('tmp.easyccg.parsed.txt')
        except FileNotFoundError:
            eprint('please specify filename of parser output, using -f')
            exit()

    idx_cant_polarize = {}
    for idx in trees.tree_idxs:
        # build the tree here
        t = trees.build_one_tree(idx, args.parser)

        # print()
        # print('-' * 20)
        # print('tree {}\n'.format(idx))
        print('{}\t'.format(idx), end="")

        if args.verbose in [0, 4]:
            t.printSent()
            t.printTree()

        # fix tree
        t.fixQuantifier()
        t.fixNot()
        if args.parser == 'candc': t.fixRC()  # only fix RC for candc

        try:
            if args.verbose in [1, 4]: t.printTree()

            t.mark()
            if args.verbose in [2, 4]: t.printTree()

            t.polarize()
            if args.verbose in [3, 4]: t.printTree()
        except (ErrorCompareSemCat, ErrorCCGtree) as e:
            idx_cant_polarize[idx] = type(e).__name__
            # print(e)
            print("Polarizing error:", type(e).__name__, end="; ")
            t.printSent_raw_no_pol()
            continue

        t.getImpSign()

        t.printSent_raw()
        # t.printSent()
        # t.printSentLatex()

        # testTrees(trees)

    # return
    print("\ncannot polarize the following trees:")
    for idx, e in sorted(idx_cant_polarize.items()):
        print(idx, e)

    print("\n\ncannot polarize {} trees".format(len(idx_cant_polarize)))

def testTrees(trees):
    '''  test other constructors of CCGtree: passed  '''
    t = trees.trees[3]
    node = t.root.children[0].children[0]
    print(node)

    newtree = CCGtree(NonTermNode=node)
    newtree.printTree()
    print(newtree.words)
    print(newtree.wholeStr)

def test():
    # # test semcat assign recursive
    # # passed
    # mycat = Cat(originalType=r'((S[ng]\NP)/NP)/PR')
    # print(mycat.semCat)
    # exclude = {"((e,t),t)", "t", "pp", "pr"}
    # mycat.semCat.assignRecursive("+", exclude)
    # print(mycat.semCat)
    #
    # return
    #
    # """ test compareSemCat(): passed """
    # left = Cat(originalType=r'(S[dcl]\NP)/NP')
    # left.semCat.marking = '+'
    # left.semCat.OUT.marking = '+'
    #
    # right = Cat(originalType=r'(S[dcl]\NP)/NP')
    # right.semCat.IN.marking = '-'
    #
    # t = CCGtree()
    # t.compareSemCat(right.semCat, left.semCat, 'parent')
    #
    # return

    ''' test Cat constructor '''
    x = Cat(originalType=r'S[dcl]/(S[dcl]\NP)')
    print(x)
    print(x.semCat)
    print(x.semCat.IN)
    print(x.semCat.OUT)
    print()

    right = Cat(originalType=r'(S\NP)\(S\NP)')
    right.semCat.marking = '+'
    right.semCat.IN.marking = '+'
    right.semCat.OUT.marking = '+'

    left = Cat(originalType=r'(S\NP)\(S\NP)')
    left.semCat.marking = '+'
    left.semCat.IN.marking = '+'
    left.semCat.OUT.marking = '+'
    print(right.semCat)

    rightCopy = copy.deepcopy(right)
    print(rightCopy.semCat)

    leftCopy = copy.deepcopy(left)
    print(leftCopy.semCat)

    conj = Cat()
    conj.right = rightCopy
    conj.left = Cat()
    conj.left.right = leftCopy
    conj.left.left = leftCopy
    print(conj.right)
    # passed the test:
    # cat = Cat(originalType=r'((S[X=true]\NP)\(S[X=true]\NP))\((S[X=true]\NP)\(S[X=true]\NP))')
    # cat = Cat(originalType=r'(S[dcl=true]\NP)/(S[b=true]\NP)')

def eprint(*args, **kwargs):
    """ print to stderr """
    print(*args, file=sys.stderr, **kwargs)

class CCGtrees:
    def __init__(self, fn_log):
        self.trees = {}
        self.numTrees = 0
        self.CandC_xml = {}    # { tree_idx : candc_xml   }
        self.easyccg_str = {}  # { tree_idx : easyccg_str }
        self.changes = {}      # { tree_idx : {'before':at most 5, 'after':no, 'idx':0}  }
        self.readLog(fn_log)   # "test.tok.preprocess.log"
        self.tree_idxs = []

    def readLog(self, log_fn):
        """ read log for pre processing """
        # log_fn: test.tok.preprocess.log
        eprint("\nreading log file: {}".format(log_fn))
        with open(log_fn) as f:
            for line in f:
                if line.startswith('sentId'): continue
                line_l = line.split(',')
                sentId, before, after, idx = int(line_l[0]), line_l[1], line_l[2], int(line_l[3])
                # may have multiple changes per sentence
                if sentId in self.changes:
                    self.changes[sentId].append({'before':before, 'after':after, 'idx':idx})
                else:
                    self.changes[sentId] = [ {'before':before, 'after':after, 'idx':idx} ]
        eprint("reading log file done!\n")

    def idx2change(self, idx):
        """ return the changes made to one tree """
        return self.changes.get(idx, None)

    def readCandCxml(self, xml_fn, treeIdxs=None):  # treeIdx starts at 0
        eprint('reading trees from candc output')
        soup = BeautifulSoup(open(xml_fn).read(), 'lxml')
        counterSent = -1
        for ccgXml in soup.find_all('ccg'):
            counterSent += 1
            if treeIdxs:
                if counterSent not in treeIdxs: continue
            # make sure there is only one root:
            try: assert len(ccgXml.find_all('rule', recursive=False)) == 1
            except AssertionError: raise ErrorCCGtrees('more than 1 root')

            #### build the tree  ####
            # eprint('reading tree {}...'.format(counterSent))
            self.CandC_xml[counterSent] = ccgXml
            self.tree_idxs.append(counterSent)
            # if counterSent in self.changes:
            #     tree = CCGtree(ccgXml=ccgXml, changes=self.changes[counterSent])
            # else:
            #     tree = CCGtree(ccgXml=ccgXml, changes=None)
            # self.trees[counterSent] = tree

        eprint('\ntrees read in from candc output!\n\n')

    def readEasyccgStr(self, easyccg_fn, treeIdxs=None):  # treeIdx starts at 0
        eprint('reading trees from easyccg output')
        easyccg_str = open(easyccg_fn).readlines()

        # for each tree
        counterSent = -1
        for tree_str in easyccg_str:
            if tree_str.startswith('ID='): continue
            counterSent += 1
            if treeIdxs:
                if counterSent not in treeIdxs: continue
            # if counterSent == 1: break
            #### build the tree  ####
            # eprint('reading tree {}...'.format(counterSent))
            self.easyccg_str[counterSent] = tree_str
            self.tree_idxs.append(counterSent)
            # if counterSent in self.changes:
            #     tree = CCGtree(easyccg_tree_str=tree_str, changes=self.changes[counterSent])
            # else:
            #     tree = CCGtree(easyccg_tree_str=tree_str, changes=None)
            # self.trees[counterSent] = tree

        eprint('\ntrees read in from easyccg output!\n\n')

    def build_one_tree(self, idx, parser, use_lemma=True):
        # t = None
        eprint('building tree {}...'.format(idx))
        if parser == 'candc':
            t = CCGtree(ccgXml=self.CandC_xml[idx], changes=self.idx2change(idx))
        else:
            t = CCGtree(easyccg_tree_str=self.easyccg_str[idx], changes=self.idx2change(idx))
        t.use_lemma = use_lemma
        self.trees[idx] = t
        return t

class CCGtree:
    '''
    read in candc.xml parsed tree and build a CCG tree,
    while reading the xml,
    1. do necessary type shifting for types related to quantifiers and negation
    2. assign +, - to quantifiers
    3. get semantic types for each syntactic type

    Then traverse the tree again,
    1. apply van Eijck / van Benthem's algorithm to get monotonicity
    2. print out the tree

    '''
    def __init__(self, **kwargs):
        self.leafNodes = []; self.words = []; self.nonTermNodes = []
        self.root = None
        self.allNodes = []  # self.leafNodes + self.nonTermNodes

        # when making tree out of a NonTermNode/LeafNode
        # wholeStr = 'CHASED SOME CAT' / 'BIRD'
        self.wholeStr = ''

        # all the inferences we can get by using one replacement in a list
        # self.inferences = []  # a list of *first_order* CCGtrees, should have no repetition

        self.numInfTotal = 0  # total num of inferences recursively

        self.inf_depth = 0    # depth of inference: how many replacements to get here

        # a list of tuples (y1, y2), storing the two types in a 'tr' rule that should
        # be the same, i.e. the two y's in:
        #        x
        #  ------------tr
        #   (x-->y1)-->y2
        self.trTypes = []

        # build tree based on xml
        if kwargs.get('ccgXml') is not None:
            self.build_CandC(kwargs.get('ccgXml'), kwargs.get('changes'))
        elif kwargs.get('easyccg_tree_str') is not None:
            # build tree from easyccg output string
            self.build_easyccg(kwargs.get('easyccg_tree_str'), kwargs.get('changes'))
        elif kwargs.get('NonTermNode') is not None:
            # build tree from NonTermNode
            self.root = kwargs.get('NonTermNode')
            self.buildFromRoot()
        elif kwargs.get('TermNode') is not None:
            # build tree from LeafNode
            self.root = kwargs.get('TermNode')
            self.buildFromRoot()
        else:
            pass
            # raise ErrorCCGtree('wrong initialization of CCGtree!')

        self.use_lemma = kwargs.get('use_lemma')  # whether use lemma in replacement_contra()

    def buildFromRoot(self):
        self.leafNodes = []
        self.nonTermNodes = []
        self.words = []
        self.buildFromRootHelper(self.root)  # get the leafNodes
        for lfnode in self.leafNodes:
            self.words.append(lfnode.word.upper())
        # fix dummy root
        dummyRoot = NonTermNode(depth=-1)
        self.root.sisters = []
        self.root.parent = dummyRoot
        dummyRoot.children = [self.root]
        # fix wholeStr
        self.getWholeStrAllNodes()
        self.wholeStr = self.root.wholeStr
        # allNodes
        self.allNodes = self.leafNodes + self.nonTermNodes
        self.regetDepth()

    def buildFromRootHelper(self, node):
        if len(node.children) == 0:
            self.leafNodes.append(node)
        else:
            self.nonTermNodes.append(node)
            # take care of sisters
            if len(node.children) == 1:
                node.children[0].sisters = []
            else:
                node.children[0].sisters = [node.children[1]]
                node.children[1].sisters = [node.children[0]]
            # recurse
            for child in node.children:
                child.parent = node
                self.buildFromRootHelper(child)

    def getWholeStrAllNodes(self):
        self.getWholeStrAllNodesHelper(self.root)

    def getWholeStrAllNodesHelper(self, node):
        if len(node.children) == 0:
            node.wholeStr = node.word.upper()
        else:
            for child in node.children:
                self.getWholeStrAllNodesHelper(child)
            node.wholeStr = ' '.join([x.wholeStr for x in node.children]).rstrip()

    def printSent(self, stream=sys.stdout):
        """ print sent lemma by lemma """
        s = ''
        for lfnode in self.leafNodes:
            # s+='{}{}{} '.format(lfnode.word, lfnode.cat.monotonicity, self.printImpSign(lfnode.impSign))
            s += '{}{} '.format(lfnode.word, lfnode.cat.monotonicity)
        s = s.replace('DOWN', '\u2193').replace('UP', '\u2191').replace('UNK', '=')
        print(s, file=stream)
        return s

    def printSent_no_pol(self, stream=sys.stdout):
        """ print sent lemma by lemma, no polarization """
        s = ''
        for lfnode in self.leafNodes:
            s += '{} '.format(lfnode.word)
        eprint(s)
        return s

    def printSent_raw(self, stream=sys.stdout):
        """ print sent word by word, not lemma by lemma """
        s = ''
        for lfnode in self.leafNodes:
            s += '{}{} '.format(lfnode.word_raw, lfnode.cat.monotonicity)
        s = s.replace('DOWN', '\u2193').replace('UP', '\u2191').\
              replace('UNK', '=')
        print(s, file=stream)
        return s

    def printSent_raw_no_pol(self, stream=sys.stdout, verbose=True):
        """ print sent word by word, not lemma by lemma, w/o polarity """
        s = ''
        for lfnode in self.leafNodes:
            s += '{} '.format(lfnode.word_raw)
        if verbose: print(s, file=stream)
        return s

    def printImpSign(self, impSign):
        if impSign is None: return "\u2022"  # bullet
        return impSign

    def printSentLatex(self):
        # \mbox{\emph{No${}^{\upred}$ man${}^{\downred}$ walks${}^{\downred}$}}\\
        for lfnode in self.leafNodes:
            print('{}${{}}^{{\{}}}$'.format(lfnode.word,lfnode.cat.monotonicity)\
                  .replace('DOWN','downred').replace('UP','upred')\
                  .replace('UNK','nonered'), end=' ')
        print()

    def __str__(self):
        return ' '.join(['{} *{}*'.format(lfnode.word, lfnode.cat.monotonicity)
                         for lfnode in self.leafNodes])

    def __repr__(self):
        return self.__str__()

    def printTree(self, stream=sys.stdout):
        print('\n--- tree:\n', file=stream)
        self.printTreeHelper(self.root, stream)

    def printTreeHelper(self, node, stream=sys.stdout):
        if len(node.children) == 0: # leaf
            print("{}{}\n".format(node.depth * '   ', node), file=stream)
        else:
            print("{}{}\n".format(node.depth * '   ', node), file=stream)
            for child in node.children:
                self.printTreeHelper(child, stream)

    # def printAllInferences(self):
    #     '''  print all inferences of a ccgtree   '''
    #     print('\n--- original sentence:\n')
    #     self.printSent()
    #     self.printAllInferencesHelper(self, 1)
    #     print('\n--- {} inferences in total'.format(self.numInfTotal))
    #
    # def printAllInferencesHelper(self, ccgtree, level):
    #     if len(ccgtree.inferences) == 0:
    #         # print('no inferences!')
    #         return
    #     for inf in ccgtree.inferences:
    #         self.numInfTotal += 1
    #         print('\n*{}* replacements:'.format(level), end='\n\n')
    #         # inf.printSentLatex()
    #         # inf.printSent()
    #         print(inf.wholeStr)
    #         self.printAllInferencesHelper(inf, level+1)

    def replacement(self, k, gen_inf):
        '''  replacement for inference; k is knowledge  '''
        # nodes2repwith is a list. there might be multiple things to replace in each run.
        # e.g. beagle < [dog, animal]
        inferences = []
        nodes2repwith = []  # nodes to replace with
        neutrals = []
        nodes2repwith_neu = []   # neutral
        contras = []
        nodes2repwith_con = []   # contradiction

        for ind in range(len(self.allNodes)):
            node = self.allNodes[ind]
            node_type = node.cat.typeWOfeats
            # print('***'+node.wholeStr+'***', end='   ')
            # print('***'+node.cat.monotonicity+'***')
            if node.wholeStr in k.frags.keys() and \
                node_type == k.frags[node.wholeStr].ccgtree.root.cat.typeWOfeats:

                # replacement for once only!!
                # get index of node in node.parent.children
                i = node.parent.children.index(node)

                # --------------  inferences  ---------------- #
                # TODO check if POS/cat is the same??
                # check the monotonicity to see whether can replace
                # make sure cat is the same: e.g. NP = NP

                # EQUAL, e.g. all = each = every; men = man
                # !! only add those that have same cat !!
                for equal in k.frags[node.wholeStr].equal:  # equal is Fragment
                    if equal.ccgtree.root.cat.typeWOfeats == node_type:
                        nodes2repwith.append(equal)

                # UP
                if node.cat.monotonicity == 'UP':
                    # replace node with the first thing bigger than it
                    # print('\nfound a node to replace:', node.wholeStr)
                    # print('replace it with        :', k.frags[node.wholeStr].big[0].ccgtree.root.wholeStr)
                    # print('cat must be the same:')
                    # print(node.cat.typeWOfeats)
                    # print(k.frags[node.wholeStr].ccgtree.root.cat.typeWOfeats)

                    # !! only add those that have same cat !!
                    for big in k.frags[node.wholeStr].big:  # big is Fragment
                        if big.ccgtree.root.cat.typeWOfeats == node_type:
                            nodes2repwith.append(big)

                # DOWN
                elif node.cat.monotonicity == 'DOWN':
                    # print('cat must be the same:')
                    # print(node.cat.typeWOfeats)
                    # print(k.frags[node.wholeStr].ccgtree.root.cat.typeWOfeats)

                    # !! only add those that have same cat !!
                    for small in k.frags[node.wholeStr].small:  # big is Fragment
                        if small.ccgtree.root.cat.typeWOfeats == node_type:
                            nodes2repwith.append(small)

                # --------------  neutrals  ---------------- #
                if gen_inf:
                    if (node.cat.monotonicity == 'UP') and (len(k.frags[node.wholeStr].small) != 0):
                        # replace with smaller sets
                        for small in k.frags[node.wholeStr].small:  # small is Fragment
                            if small.ccgtree.root.cat.typeWOfeats == node_type:
                                nodes2repwith_neu.append(small)

                    elif (node.cat.monotonicity == 'DOWN') and (len(k.frags[node.wholeStr].big) != 0):
                        # replace with bigger sets
                        for big in k.frags[node.wholeStr].big:  # big is Fragment
                            if big.ccgtree.root.cat.typeWOfeats == node_type:
                                nodes2repwith_neu.append(big)

                # --------------  contras  ---------------- #
                for ant in k.frags[node.wholeStr].ant:  # todo: replace w/ ant results in contra?
                    if ant.ccgtree.root.cat.typeWOfeats == node_type:
                        nodes2repwith_con.append(ant)

                # --------------  contras  ---------------- #
                # alternations
                if node.cat.monotonicity == 'UP':
                    # TODO
                    if len(k.frags[node.wholeStr].alter) != 0:
                        # replace with alternations
                        for alter in k.frags[node.wholeStr].alter:  # alter is Fragment
                            if alter.ccgtree.root.cat.typeWOfeats == node_type:
                                nodes2repwith_con.append(alter)

                # if there are nodes to replace
                if nodes2repwith:
                    inferences.extend(self.replacement_helper(node, nodes2repwith, ind, i, at_least=False))

                if nodes2repwith_neu:
                    neutrals.extend(self.replacement_helper(node, nodes2repwith_neu, ind, i, at_least=False))

                if nodes2repwith_con:
                    contras.extend(self.replacement_helper(node, nodes2repwith_con, ind, i, at_least=False))

                nodes2repwith = []
                nodes2repwith_neu = []
                nodes2repwith_con = []

            # at-least N < some = a = an, N = 3, 5, several
            elif node.wholeStr.startswith("AT-LEAST") and \
                    len(node.wholeStr.split(' ')) == 2:
                # [some, a, an]
                nodes2repwith = [n for n in k.frags["AT-LEAST-N"].big]
                i = node.parent.children.index(node)  # index of 'at-least-N' in parent
                eprint("replacing at least N")
                # do replacement, SAME AS ABOVE
                inferences.extend(self.replacement_helper(node, nodes2repwith, ind, i, at_least=True))
                nodes2repwith = []

        return inferences, neutrals, contras

    def replacement_helper(self, node, nodes2repwith, ind, i, at_least):
        ans = []  # inferences or neutrals

        for newNode in nodes2repwith:  # newNode is a Fragment
            newNode = newNode.ccgtree.root
            # if node.wholeStr == 'LARGE':
            #     print(newNode)
            # -----------------------------
            # SET POS and CAT for newNode
            # !! newNode.pos, newNode.cat came from building the knowledge
            # could be incomplete
            if not at_least:  # only check if not "at least"
                try:
                    if newNode.pos is None:  # replace
                        newNode.pos, newNode.cat = node.pos, node.cat
                    elif newNode.cat.typeWOfeats == node.cat.typeWOfeats:  # replace
                        if newNode.pos == node.pos: pass
                        else: newNode.pos = node.pos
                    elif newNode.pos[0] == node.pos[0]:  # replace
                        if newNode.cat.typeWOfeats == newNode.cat.typeWOfeats:
                            pass
                        else:  # e.g. both are N, but cat are different
                            newNode.pos, newNode.cat = node.pos, node.cat
                    else:  # in all other cases, don't replace, e.g.newNode = V, node = N
                        continue
                except AttributeError:  # NonTermNode does not have pos
                    # print(newNode.cat, node.cat)
                    pass

            # --------------------------
            # NOW build new tree and add to self.inferences
            # initialize new tree
            newTree = copy.deepcopy(self)
            oldNode = newTree.allNodes[ind]  # important: locate the oldNode in newTree

            # replace oldNode w/ newNode
            newNode = copy.deepcopy(newNode)  # newNode is from K, need to make a new instance
            oldNode.parent.children[i] = newNode
            newNode.parent = oldNode.parent

            # rebuild tree
            newTree.buildFromRoot()
            newTree.regetDepth()
            newTree.mark()
            newTree.polarize()

            ans.append(newTree)
        return ans

    def replacement_contra(self):
        """ return all contradictions based on rules, contras is a list """
        # the reason not to replace every "no" with "some" is the relative clauses
        # Books that no one liked are all sold.
        # does not contradict: Books that some one liked are sold.
        contras = []

        def get_str(node, use_lemma):
            if use_lemma:
                return node.wholeStr
            else:  # word
                if len(node.children) == 0: return node.word_raw  # leaf
                else: return node.word_wholeStr()  # non term

        # if False, accuracy for contradiction will be 0!
        use_lemma = self.use_lemma  # default is True; False when only generate infs and contras

        # rule 1
        # first word: some --> no; no --> some
        if self.wholeStr.startswith("SOME"):
            contras.append("NO " + ' '.join(get_str(self.root, use_lemma).split()[1:]))
            # contras.append("NO " + ' '.join(self.wholeStr.split()[1:]))
        elif self.wholeStr.startswith("NO"):
            contras.append("SOME " + ' '.join(get_str(self.root, use_lemma).split()[1:]))
            # contras.append("SOME " + ' '.join(self.wholeStr.split()[1:]))

        # TODO rule 2
        # in object position: a/an/the/some --> no; no --> some
        # test sent: Each European has the right to live in Europe.
        # contra: Each European has no right to live in Europe.
        #                      the          right to live in Europe
        #                     NP/N                  N
        #         have      ---------------------------------------
        #       (S\NP)/NP                    NP  =  myNP
        #      ----------------------------------
        # NP                S\NP  =  VP
        # -----------------------
        #            S
        if len(self.root.children) == 2 and \
                self.root.children[1].cat.typeWOfeats == r"S\NP":
            VP = self.root.children[1]
            # make sure main verb is not "BE"
            if len(VP.children)==2 and VP.children[0].wholeStr != "BE" and \
                    VP.children[1].cat.typeWOfeats == "NP":
                myNP = VP.children[1]
                # some --> no
                if len(myNP.children) == 2 and \
                        myNP.children[0].wholeStr in {"SOME", "A", "AN", "THE"}:
                    # contra_str = VP.sisters[0].wholeStr
                    # contra_str += " " + VP.children[0].wholeStr
                    # contra_str += " " + "NO " + " ".join(myNP.wholeStr.split()[1:])
                    contra_str = get_str(VP.sisters[0], use_lemma)
                    contra_str += " " + get_str(VP.children[0], use_lemma)
                    contra_str += " " + "NO " + " ".join(get_str(myNP, use_lemma).split()[1:])
                    contras.append(contra_str)
                # no --> some
                elif len(myNP.children) == 2 and \
                                myNP.children[0].wholeStr == "NO":  # was: NEVER
                    # contra_str = VP.sisters[0].wholeStr
                    # contra_str += " " + VP.children[0].wholeStr
                    # contra_str += " " + "SOME " + " ".join(myNP.wholeStr.split()[1:])
                    contra_str = get_str(VP.sisters[0], use_lemma)
                    contra_str += " " + get_str(VP.children[0], use_lemma)
                    contra_str += " " + "SOME " + " ".join(get_str(myNP, use_lemma).split()[1:])
                    contras.append(contra_str)

        # TODO another way to implement rule 2
        # TODO use dependency parse, find the "nmod" of "dobj". then swap "no" with "some"

        # TODO rule 3
        # add "do not" before a verb
        # test sent: Each European has the right to live in Europe.
        # contra: Each European does not has right to live in Europe
        #                      the          right to live in Europe
        #                     NP/N                  N
        #         have      ---------------------------------------
        #       (S\NP)/NP = myV           NP  =  myNP
        #      ----------------------------------
        # NP                S\NP  =  VP
        #-----------------------
        #            S
        if " NOT " not in self.wholeStr and " N'T " not in self.wholeStr:
            if len(self.root.children) == 2 and \
                    self.root.children[1].cat.typeWOfeats == r"S\NP":
                VP = self.root.children[1]
                # main verb is not "BE"
                if len(VP.children) == 2 and VP.children[0].wholeStr != "BE" and \
                        VP.children[0].cat.typeWOfeats == r"(S\NP)/NP":
                    # add "do not"
                    # contra_str = VP.sisters[0].wholeStr + " DO NOT " + VP.wholeStr
                    contra_str = get_str(VP.sisters[0], use_lemma) + " DO NOT " + get_str(VP, use_lemma)
                    contras.append(contra_str)
                # main ver = BE
                elif len(VP.children) == 2 and VP.children[0].wholeStr == "BE":
                    # the person is slicing a garlic -> the person is not slicing ...
                    # contra_str = VP.sisters[0].wholeStr + " BE NOT " + VP.children[1].wholeStr
                    contra_str = get_str(VP.sisters[0], use_lemma) + " BE NOT " + get_str(VP.children[1], use_lemma)
                    contras.append(contra_str)

        # sent: a man (is (recklessly climbing a rope))
        # contra: a man is climbing a rope
        # TODO: recklessly climb a rope < climb a rope


        # TODO rule 4: if not in sent, then remove not, what if two negations
        if " NOT " in self.wholeStr:
            # contras.append(self.wholeStr.replace(" NOT", ""))
            contras.append(get_str(self.root, use_lemma).replace(" NOT", "").replace(" not", "").replace("Not", ""))
        if " N'T " in self.wholeStr:
            # contras.append(self.wholeStr.replace(" N'T", ""))
            contras.append(get_str(self.root, use_lemma).replace(" N'T", "").replace(" n't", ""))

        # TODO rule 5:
        # sent: There is no boy walking across a bridge
        # contra: A/the/an/some boy is walking across a bridge
        if self.wholeStr.startswith("THERE BE NO"):
            # find the subj: boy. Maybe use dep parse???
            # subj = self.wholeStr.split()[3]  # TODO this assumes subj has only one word!
            subj = get_str(self.root, use_lemma).split()[3]  # TODO this assumes subj has only one word!
            for quant in ["A", "THE", "AN", "SOME"]:
                contra_str = quant + " " + subj + " BE " + ' '.join(get_str(self.root, use_lemma).split()[4:])
                contras.append(contra_str)

            # TODO dependncy tree


        # TODO another way is to find contra from both directions: P->H, H->P
        # this should make implementation easier

        return contras

    def transform_RC2JJ(self):
        """ relative clause to adjective
        a dog which is black is running -> a black dog is running """
        new_trees = []

        # find RC
        for i, lfnode in enumerate(self.leafNodes):
            if lfnode.wholeStr in RC_PRON:
                RC = lfnode.parent.wholeStr.lower()
                len_RC = len(RC.split())
                if len_RC == 3 and RC.split()[1] == "be":  # e.g. which is little
                    new_tree = copy.deepcopy(self)   # need a new tree
                    lfnode = new_tree.leafNodes[i]   # lfnode has to be in the new_tree!

                    # kangaroo that be little
                    #                   that           be little
                    #                                 ----------
                    #               (N\N)/(S\NP)         (S\NP)
                    # kangaroo    ---------------------------------
                    #    N = N_node            N\N
                    # ----------------------------
                    #              N = full_N_node
                    full_N_node = lfnode.parent.parent
                    N_node = lfnode.parent.parent.children[0]
                    ADJ_node = lfnode.sisters[0].children[1]
                    # print("ADJ:", ADJ_node)
                    if not hasattr(ADJ_node, 'pos'):
                        ADJ_node = ADJ_node.children[0]
                        # print(ADJ_node)
                    # ADJ_node can either be a JJ
                    # or a nonTermNode: NP lex from another word

                    # eprint("N  :", N_node)
                    # eprint("N f:", full_N_node)
                    # eprint()

                    if full_N_node.cat.typeWOfeats != "N":
                        eprint("full_N_node not N")
                        break  # can't handle it
                    if ADJ_node.cat.typeWOfeats not in {r"S\NP", r"N"}:
                        eprint(r"ADJ_node not S\NP or N")
                        break  # can't handle it
                    if N_node.cat.typeWOfeats != "N":
                        eprint("N_node not N")
                        break  # can't handle it

                    # --------------------------------
                    # build a new full_N_node, and adjust pointers
                    # ADJ can be of type: S\NP, N
                    # both needs to be converted to N/N
                    ADJ_word = ADJ_node.wholeStr.lower()
                    ADJ_node_new = LeafNode(depth=0, cat=Cat(originalType=r"N/N", word=ADJ_word),
                                            chunk=None, entity=None, lemma=ADJ_word, pos="JJ",
                                            span=None, start=None, word=ADJ_word)
                    full_N_node_new = NonTermNode(depth=0, cat=Cat(originalType="N"), ruleType="fa")
                    N_node.parent, ADJ_node_new.parent = full_N_node_new, full_N_node_new
                    full_N_node_new.children = [ADJ_node_new, N_node]

                    if full_N_node.parent:  # if full_N_node has a parent
                        idx_full_N_node_in_parent = full_N_node.parent.children.index(full_N_node)
                        full_N_node.parent.children[idx_full_N_node_in_parent] = full_N_node_new
                        full_N_node_new.parent = full_N_node.parent
                        full_N_node.parent = None
                    else:
                        eprint("full_N_node has no parent")
                        break  # can't handle it

                    new_tree.buildFromRoot()
                    new_tree.regetDepth()
                    new_tree.mark()
                    new_tree.polarize()

                    # new_tree.printSent(stream=sys.stderr)
                    new_trees.append(new_tree)

        return new_trees

    def transform_JJ2RC(self):
        """ 2622
        A man is wearing a hard hat and dancing
        A man is wearing a hat which is hard and is dancing """
        new_trees = []

        return new_trees

    # def replaceRC(self):
    #     '''
    #     e.g. some young man [who likes dogs] likes cats
    #     infer: some man likes cats
    #     Remove restrictive RC if it has *UP* polarity; then add to
    #      CCGTree.inferences
    #     '''
    #     # detect all nonTermNodes which are RCs with polarity *UP*:
    #     RCs = []
    #     for node in self.nonTermNodes:
    #         if node.cat.typeWOfeats == r'NP\NP' and \
    #                 node.children[0].wholeStr.upper() in ['THAT','WHO','WHOM','WHICH']:
    #             if node.cat.monotonicity == 'UP':
    #                 RCs.append(node)
    #
    #     # remove RC and add to inferences
    #
    #     # old tree:
    #     #   N young man      NP\NP who likes dogs => RC
    #     #  ------------lex
    #     #    NP  => NP1
    #     #   ----------------------------- fa
    #     #                 NP  => NP2
    #     #             ---------unlex (my rule)
    #     #  NP/N some      N
    #     #  ------------------
    #     #        NP
    #
    #     # now we want to move NP1 to NP2
    #     #            N young man
    #     #           ------------lex
    #     #                NP
    #     #             ---------unlex (my rule)
    #     #  NP/N some      N
    #     #  ------------------
    #     #        NP
    #
    #     for RC in RCs:
    #         # initialize new tree
    #         newTree = copy.deepcopy(self)  # TODO
    #         newTree.inferences = []
    #
    #         # get index of RC in nonTermNodes
    #         ind = self.nonTermNodes.index(RC)
    #         RC  = newTree.nonTermNodes[ind]  # RC should be in newTree
    #
    #         # get NP1 and NP2
    #         node_NP1 = RC.sisters[0]
    #         node_NP2 = RC.parent
    #
    #         # adjust pointer
    #         # indNP2 is the index of NP2 in NP2.parent.children
    #         indNP2 = node_NP2.parent.children.index(node_NP2)
    #         node_NP2.parent.children[indNP2] = node_NP1
    #         node_NP1.parent = node_NP2.parent
    #
    #         # rebuild the tree; this takes care of:
    #         # self.nonTermNodes, self.leafNodes and self.allNodes
    #         newTree.buildFromRoot()
    #         newTree.regetDepth()
    #         newTree.mark()
    #         newTree.polarize()
    #
    #         # sanity check
    #         # newTree.printSent()
    #         # newTree.printTree()
    #         # print(len(newTree.leafNodes))
    #         # print(len(newTree.nonTermNodes))
    #         # print(len(newTree.allNodes))
    #
    #         self.inferences.append(newTree)

    def getAllDescendants(self, nonTermNode):
        ''' Returns a list of all descendants of a nonTermNode (including itself) '''
        des = []
        self.getAllDescendantsHelper(nonTermNode, des)
        return des

    def getAllDescendantsHelper(self, node, des):
        des.append(node)
        if len(node.children) > 0:
            for child in node.children:
                self.getAllDescendantsHelper(child, des)

    def assignEqualMarkingTR(self):
        """ make sure 2y's in 'tr' have the same markings """
        for y in self.trTypes:  # for each pair of ys
            self.assignEqualMarkingTRHelper(y[0], y[1])

    def assignEqualMarkingTRHelper(self, semCat1, semCat2):
        """ assign equal markings, used for post-processing 2 y's in 'tr' rule
            x
        ---------tr
        (x-->y)-->y
        e.g. semCat1: (((e,t),t),+t) semCat2: (((e,t),-t),t)
        result: semCat1 = semCat2 = (((e,t),-t),+t)
        """
        try: assert semCat1.semCatStr == semCat2.semCatStr  # semCatStr does not have +/-
        except AssertionError: raise ErrorAssignEqualMarking("semCatStr not the same {}; {}".\
                                          format(semCat1, semCat2))
        try: assert (semCat1.marking is None) or (semCat2.marking is None) \
                    or (semCat1.marking == semCat2.marking)
        except AssertionError:
            raise ErrorAssignEqualMarking("conflicting markings {}; {}".\
                                          format(semCat1, semCat2))
        # assign marking
        if semCat1.marking is None: semCat1.marking = semCat2.marking
        if semCat2.marking is None: semCat2.marking = semCat1.marking
        # recurse
        if semCat1.IN: self.assignEqualMarkingTRHelper(semCat1.IN, semCat2.IN)
        if semCat1.OUT: self.assignEqualMarkingTRHelper(semCat1.OUT, semCat2.OUT)

    def mark(self):
        ''' add plus minus to all nodes '''
        self.mark_LeafNodes()
        self.mark_NTN()

        # post-processing
        self.assignEqualMarkingTR()

        # equate markings if needed
        # TODO more compliccated than I thought
        # TODO have to propogate much further up the tree
        for node in self.leafNodes + self.nonTermNodes:
            if node.cat:  # if not None
                if node.cat.typeWOfeats == r'(S\NP)/(S\NP)':
                    # eprint('equate marking:', node)
                    self.equate_marking(node.cat.semCat.IN, node.cat.semCat.OUT)
                    # eprint('after equate marking:', node)

    def mark_LeafNodes(self):
        ''' mark leaf nodes '''
        for token in self.leafNodes:
            # -----------------------
            # quantifiers   TODO what if not of type NP/N
            if token.word.upper() in {'SOME', 'A', 'AN', 'SEVERAL','ONE','2','3','4','5'}:  # + +
                # if token.cat.semCat.semCatStr == '((e,t),((e,t),t))':
                try:
                    token.cat.semCat.marking = '+'
                    token.cat.semCat.OUT.marking = '+'
                except AttributeError: pass
            elif token.word.upper() in {'EVERY', 'ALL', 'EACH'}:  # - +
                # if token.cat.semCat.semCatStr == '((e,t),((e,t),t))':
                token.cat.semCat.marking = '-'
                token.cat.semCat.OUT.marking = '+'
            elif token.word.upper() in {'NO', 'FEW'}:  # - -
                # if token.cat.semCat.semCatStr == '((e,t),((e,t),t))':
                token.cat.semCat.marking = '-'
                token.cat.semCat.OUT.marking = '-'
            elif token.word.upper() in {'BOTH', 'EITHER', 'MANY', 'MOST', 'THE'}:
                token.cat.semCat.OUT.marking = '+'
            elif token.word.upper() in {'NEITHER'}:
                token.cat.semCat.OUT.marking = '-'
            # TODO other DTs: this, that?

            elif token.pos.upper() == "PRP$":  # pos
                token.cat.semCat.assignRecursive("+", EXCLUDE)
                pass

            # -----------------------
            # at-most, at-least
            elif token.note == "at-most":
                # (NP/N)/(N/N)
                # ((et,et),+(et-,(et-,t)))
                token.cat.semCat.marking = '+'
                token.cat.semCat.OUT.marking = '-'
                token.cat.semCat.OUT.OUT.marking = '-'
            elif token.note == "at-least":
                # (NP/N)/(N/N)
                # ((et,et),-(et+,(et+,t)))
                token.cat.semCat.marking = '-'
                token.cat.semCat.OUT.marking = '+'
                token.cat.semCat.OUT.OUT.marking = '+'

            # -----------------------
            # TODO negation
            elif token.word.upper() in {'NOT', "N'T"}:  # N'T: (S\NP)\(S\NP)
                token.cat.semCat.marking = '-'  # check semCatStr??
                # TODO is this correct?
                if token.cat.typeWOfeats != r"N/N":
                    token.cat.semCat.OUT.marking = '+'
                    token.cat.semCat.IN.marking = '+'
                    # token.cat.semCat.OUT.IN.marking = '+'  # (S+\NP+)-\(S+\NP)
                    # token.cat.semCat.IN.IN.marking = '+'  # (S+\NP)-\(S+\NP+)

            # -----------------------
            # TODO nouns
            # nobody DT, NP
            elif token.word.upper() == "NOBODY":
                if token.cat.typeWOfeats == "NP":
                    token.cat.semCat.marking = "-"
            # if the leafNode is NP, e.g. pronouns such as I, make it NP+
            elif token.cat.originalType == 'NP':
                token.cat.semCat.marking = '+'
                # token.cat.semCat.OUT.marking = token.cat.semCat.IN.marking = '+'
            elif token.word.upper() == 'IT':
                token.cat.semCat.marking = '+'

            # -----------------------
            # TODO noun can be: N/(S\NP)
            # e.g. the `right` to live in Europe
            elif (token.pos.upper() == 'NN') and \
                    (token.cat.typeWOfeats == r'N/(S\NP)'):
                token.cat.semCat.marking = '+'
                token.cat.semCat.IN.marking = '+'
                token.cat.semCat.IN.IN.marking = '+'
            # TODO NNS, NN
            elif token.pos.upper().startswith("NN"):
                token.cat.semCat.assignRecursive("+", EXCLUDE)

            # THERE BE
            elif token.pos.upper() == "EX":
                if token.word.upper() == "THERE":
                    if token.cat.semCat.semCatStr == "((e,t),t)":
                        token.cat.semCat.marking = "+"

            # -----------------------
            # if = (t,-(t,+t))
            elif token.word.upper() == 'IF':
                token.cat.semCat.marking = '-'
                token.cat.semCat.OUT.marking = '+'
            elif token.word.upper() == 'THEN':
                token.cat.semCat.marking = '+'

            # that, who
            elif token.word.upper() in ['THAT', 'WHO', 'WHICH'] and \
                    (token.pos in ['WDT', 'IN', 'WP']):
                # !! already handled in Cat() !! #
                pass

            # TODO verbs
            elif token.pos.upper().startswith('VB'):
                # TODO add monotone DOWN verbs
                if token.lemma.upper() in ['REFUSE', 'FAIL'] and \
                        token.cat.typeWOfeats == r'(S\NP)/(S\NP)':
                    token.cat.semCat.marking = '-'
                    token.cat.semCat.OUT.marking = '+'
                    token.cat.semCat.IN.marking = '+'  # (S+\NP)-/(S+\NP)
                    # token.cat.semCat.IN.IN.marking = '+'
                    # token.cat.semCat.OUT.IN.marking = '+'  # (S+\NP+)-/(S+\NP+)

                else:
                    token.cat.semCat.marking = '+'
                    if token.cat.typeWOfeats == r'(S\NP)/NP':  # transitive verb
                        token.cat.semCat.OUT.marking = '+'  # make it (S+\NP)+/NP
                    elif token.cat.typeWOfeats == r'((S\NP)/PP)/NP':  # 'put' with a PP argument
                        token.cat.semCat.OUT.marking = '+'
                        token.cat.semCat.OUT.OUT.marking = '+'  # make it ((S\+NP)/+PP)+/NP
                    # elif (token.word.upper() in ['DID', 'DO']) and \
                    #         (token.cat.typeWOfeats == r'(S\NP)/(S\NP)'):  # 'did' in 'did not'
                    elif token.cat.typeWOfeats == r'(S\NP)/(S\NP)':
                        # 'did' in 'did not', 'want' in I want to go
                        token.cat.semCat.OUT.marking = '+'
                        token.cat.semCat.IN.marking = '+'  # (S+\NP)+/(S+\NP)
                        # token.cat.semCat.IN.IN.marking = '+'   # (S+\NP)+/(S+\NP+)
                        # token.cat.semCat.OUT.IN.marking = '+'  # (S+\NP+)+/(S+\NP)
                    elif token.cat.typeWOfeats == r'(S\NP)/PP':  # 'ask' as in 'ask about'
                        token.cat.semCat.OUT.marking = '+'
                    elif token.cat.typeWOfeats == r'(S\NP)/N':
                        token.cat.semCat.OUT.marking = '+'
                    elif token.cat.typeWOfeats == r'(S\NP)/PR':
                        token.cat.semCat.OUT.marking = '+'
                    elif token.cat.typeWOfeats == r'((S\NP)/NP)/PR':
                        token.cat.semCat.OUT.marking = '+'
                        token.cat.semCat.OUT.OUT.marking = '+'
                    else:
                        token.cat.semCat.assignRecursive("+", EXCLUDE)


            # TODO model verbs
            elif token.pos.upper() == 'MD' and token.cat.typeWOfeats != 'N':
                # can: (S\NP)/(S\NP)
                token.cat.semCat.marking = '+'
                token.cat.semCat.IN.marking = '+'  # ??
                token.cat.semCat.OUT.marking = '+'  # ??

            # TODO to
            # elif (token.pos.upper() == 'TO') and \
            #         (token.cat.typeWOfeats == r'(S\NP)/(S\NP)'):
            #     # 'to' in 'I want to', 'refused to' # (S+\NP)+/(S+\NP)
            #     token.cat.semCat.marking = '+'
            #     token.cat.semCat.OUT.marking = '+'
            #     token.cat.semCat.IN.marking = '+'
            #     # token.cat.semCat.OUT.IN.marking = '+'
            #     # token.cat.semCat.IN.IN.marking = '+'  # (S+\NP+)+/(S+\NP+)
            elif token.pos.upper() == 'TO':
                token.cat.semCat.assignRecursive("+", EXCLUDE)

            # TODO adverbs 1
            elif (token.pos.upper() == 'RB') and \
                    (token.word.upper() not in ['NOT', "N'T"]):
                if token.cat.typeWOfeats in [r'(S\NP)/(S\NP)', r'(S\NP)\(S\NP)'] :
                    # adverbs; make it (S+\NP)+/(S+\NP)
                    token.cat.semCat.marking = '+'
                    token.cat.semCat.OUT.marking = token.cat.semCat.IN.marking = '+'
                elif token.cat.typeWOfeats in [r'S\NP']:
                    # adverbs; make it S+\NP
                    token.cat.semCat.marking = '+'
                elif token.cat.typeWOfeats in [r'(S\NP)/PP']:
                    # as fast as him, fast = (S\NP)/PP
                    token.cat.semCat.marking = '+'
                    token.cat.semCat.OUT.marking = '+'
                # TODO all other adverbs
                else:
                    token.cat.semCat.assignRecursive("+", EXCLUDE)

            # -----------------------
            # TODO adjectives, add +
            elif token.pos.upper().startswith('JJ'):
                if token.word.upper() not in ['FAKE','FORMER']:
                    # token.cat.semCat.marking = '+'
                    token.cat.semCat.assignRecursive("+", EXCLUDE)

            # noun as noun modifiers, add +
            elif (token.pos.upper() in ['NN', 'NNP']) and \
                    (token.cat.typeWOfeats == r'N/N'):
                token.cat.semCat.marking = '+'

            # TODO than
            elif token.word.upper() == "THAN":
                if token.cat.typeWOfeats == r'((S\NP)\(S\NP))/NP':
                    # ((S+\NP)+\(S+\NP))+/NP
                    token.cat.semCat.marking = '+'
                    token.cat.semCat.OUT.marking = '+'
                    token.cat.semCat.OUT.IN.marking = '+'
                    token.cat.semCat.OUT.OUT.marking = '+'


            # TODO prepositions
            elif token.word.upper() in {'IN', 'ON', 'TO', 'FROM', 'FOR',
                                        'WITHIN', 'OF', 'AT', 'BY', 'INTO'}:
                # prepositions like 'in' as an argument, as in 'He puts it in the box'
                if token.cat.typeWOfeats == 'PP/NP':
                    token.cat.semCat.marking = '+'  # make it PP/+NP'

                # 'in' as an adjunct as in 'John sleeps in France'
                # 'to' as in 'go to bed'
                elif token.cat.typeWOfeats == r'((S\NP)\(S\NP))/NP':
                    # TODO important!! the first 2 NPs should be None
                    # make it ((S+\NP)+\(S+\NP))+/NP
                    token.cat.semCat.marking = '+'
                    token.cat.semCat.OUT.marking = '+'
                    token.cat.semCat.OUT.OUT.marking = '+'
                    token.cat.semCat.OUT.IN.marking = '+'
                    # token.cat.semCat.OUT.IN.IN.marking = '+'
                    # token.cat.semCat.OUT.OUT.IN.marking = '+'

                # 'in' as a modifier for nouns as in 'the man in France sleeps'
                # candc: (NP\NP)/NP; easyccg: (N\N)/NP
                elif token.cat.typeWOfeats in [r'(NP\NP)/NP', r'(N\N)/NP']:
                    # make it (NP+\NP)+/NP
                    token.cat.semCat.marking = '+'
                    token.cat.semCat.OUT.marking = '+'

                # 'in' in a PP that serves as sentential adverb, as in 'In theory, ...'
                elif token.cat.typeWOfeats in [r'(S/S)/NP', r'(S\S)/NP']:
                    # make it (S+/S)+/NP
                    token.cat.semCat.marking = '+'
                    token.cat.semCat.OUT.marking = '+'

            elif token.word.upper() in DE_PREP:  # out, without, outside
                if token.cat.typeWOfeats == r'((S\NP)\(S\NP))/NP':  # without
                    token.cat.semCat.marking = '-'
                    token.cat.semCat.OUT.marking = '+'
                    token.cat.semCat.OUT.IN.marking = '+'
                    token.cat.semCat.OUT.OUT.marking = '+'
                    # token.cat.semCat.OUT.IN.IN.marking = '+'
                    # token.cat.semCat.OUT.OUT.IN.marking = '+'  # ((S+\NP+)+\(S+\NP+))-/NP
                elif token.cat.typeWOfeats == r'(S\NP)\(S\NP)':
                    # `they are playing outside`
                    token.cat.semCat.marking = '-'
                    token.cat.semCat.OUT.marking = '+'
                    token.cat.semCat.IN.marking = '+'
                elif token.cat.typeWOfeats == r'S\NP':
                    token.cat.semCat.marking = '+'  # 'out' in '2 men are looking out'
                else:
                    token.cat.semCat.marking = '-'
                    if token.cat.semCat.IN:
                        token.cat.semCat.IN.assignRecursive("+", EXCLUDE)
                    if token.cat.semCat.OUT:
                        token.cat.semCat.OUT.assignRecursive("+", EXCLUDE)

            elif token.pos.upper() == "IN":
                token.cat.semCat.assignRecursive("+", EXCLUDE)

            elif token.pos.upper() == "RP":  # preposition??
                token.cat.semCat.assignRecursive("+", EXCLUDE)

    def mark_NTN(self):
        ''' mark non terminal node '''
        self.mark_NTN_helper(self.root)
        # get marking for conj
        # self.mark_NTN_helper_conj(self.root)

    def mark_NTN_helper(self, node):
        # we can only set our parent when all its DESCENDANTS
        # have been set

        # no sisters
        if len(node.sisters) == 0:
            # print('\n\nnode:', node)
            # print('no sister')
            if node.visited:  # either leafNode or a visited parent of a unary rule
                # print('\n\nnode visited:', node)
                pass
            else:  # an unvisited parent of a unary rule
                # print('\n\nnode not visited:', node)
                for child in node.children:
                    # print('child:', child)
                    self.mark_NTN_helper(child)

            # IMPORTANT: now all its descendants have been marked!
            # so we can set node.parent
            if node.parent.ruleType == 'conj': self.mark_NTN_myparent_conj(node)
            else: self.mark_NTN_myparent(node)

        # 1 sister
        elif len(node.sisters) == 1:
            # only if BOTH me and my sister have been marked,
            # can we set marking for parent
            # I can either be 'left' or 'right', so is my sister
            parent = node.parent
            left = parent.children[0]
            right = parent.children[1]
            if left.visited and right.visited: pass
            # whoever is not visited, we should recurse down
            elif left.visited and (not right.visited):
                for child in right.children: self.mark_NTN_helper(child)
            elif (not left.visited) and right.visited:
                for child in left.children: self.mark_NTN_helper(child)
            elif (not left.visited) and (not right.visited):
                for child in left.children: self.mark_NTN_helper(child)
                for child in right.children: self.mark_NTN_helper(child)
            else:
                raise ErrorCCGtree('something wrong in mark_NTN_helper()')
        else:
            raise ErrorCCGtree('number of sisters more than 1: {}'.format(node))

        # check all descendants are marked
        if len(node.children) != 0:
            for child in node.parent.children: assert child.visited
        # now all its descendants have been marked! Mark node.parent
        # but only do this when parent not already set by my sister
        if not node.parent.visited:
            self.mark_NTN_myparent(node)
        if node.parent.ruleType == 'conj':
            self.mark_NTN_myparent_conj(node)

        node.visited = True

    def mark_NTN_myparent(self, node):
        ''' assign the marking of node.parent '''

        # if I'm single child, then rule can be 'lex', 'tr', 'unlex'
        if len(node.sisters) == 0:
            # eprint('\n\n-- Now getting parent')
            # eprint('I am node:', node)
            if node.depth != 0:
                # eprint('my parent before:', node.parent)
                pass

            if node.parent.ruleType == 'tr':
                node.parent.cat.semCat.marking = '+'
                # * syntactically 2 possibilities:
                #   X                  X
                # -------     or     -------
                # Y\(Y/X)            Y/(Y\X)
                # * but semantically only 1:
                #     x
                # --------- tr
                # (x->y)->y
                # make sure the markings on x is populated down
                # eprint(node.parent.cat.semCat)
                # eprint(node.cat.semCat)
                node.parent.cat.semCat.IN.IN.marking = node.cat.semCat.marking  # TODO
                # eprint(node.parent.cat.semCat)
                # eprint(node.cat.semCat)
                # store the 2 y's in self.trTypes
                self.trTypes.append( (node.parent.cat.semCat.IN.OUT,
                                      node.parent.cat.semCat.OUT) )
                # eprint('------')
                # eprint(node)
                # eprint(node.parent)
            elif node.parent.ruleType == 'lex':
                # probably we don't have to do anything
                # 'lex' happens for 'John' or 'reading' in 'this is the book that
                #   I burnt without reading'
                # we want 'John' to be NP+
                # eprint('node:', node)
                node.parent.cat.semCat.marking = '+'
                # eprint('node.parent:', node.parent)
            elif node.parent.ruleType == 'unlex':
                # NP -> N: rule added by me, for RC, do nothing
                pass
            else:  # terminal node
                pass

        # if I got one sister
        elif len(node.sisters) == 1:
            parent = node.parent
            left = parent.children[0]
            right = parent.children[1]

            if node.depth != 0:
                pass
            if parent.ruleType == 'fa':
                # X/Y Y -> X
                # make sure input and output of FA is correct
                # may not be true after fixQuantifier: e.g. Several man in a competition are running in door
                try:
                    assert parent.cat.semCat.semCatStr == left.cat.semCat.OUT.semCatStr
                    assert left.cat.semCat.IN.semCatStr == right.cat.semCat.semCatStr
                except AssertionError:
                    eprint("Error in fa, likely due to fixQuantifier:")
                    eprint(parent, ";  ", left, ";  ", right)
                parent.cat.semCat = left.cat.semCat.OUT  # assign marking

                # TODO comparator
                self.compareSemCat(left.cat.semCat.IN, right.cat.semCat, parent)
                # left.cat.semCat.IN = right.cat.semCat

            elif parent.ruleType == 'ba':
                # Y X\Y -> X
                # make sure input and output of BA is correct
                assert parent.cat.semCat.semCatStr == right.cat.semCat.OUT.semCatStr
                assert right.cat.semCat.IN.semCatStr == left.cat.semCat.semCatStr

                # --- FOR RELATIVE CLAUSES --- #
                # TODO: COULD BE DELETED NOW since fixTree() fixes the RC
                # if X\Y is NP\NP, the RC in English (English RC comes after the head NP)
                # TODO, ONLY do this for RC, but NOT conjunction!
                if (right.cat.typeWOfeats == r'NP\NP') and \
                        (right.ruleType.upper() != 'CONJ'):
                    # then the OUT NP should have the same marking as the IN NP in right
                    # assert right.cat.semCat.OUT.marking is None
                    right.cat.semCat.OUT.marking = left.cat.semCat.marking
                # --- END: FOR RELATIVE CLAUSES --- #

                parent.cat.semCat = right.cat.semCat.OUT  # assign marking

                # TODO comparator
                self.compareSemCat(right.cat.semCat.IN, left.cat.semCat, parent)  # IMPORTANT
                # right.cat.semCat.IN = left.cat.semCat

            elif parent.ruleType == 'bx':
                # two possibilities
                # X/Y Y\Z -> X\Z
                if parent.cat.direction == 'l':
                    # if left.cat.right.typeWOfeats == right.cat.left.typeWOfeats:
                    # make sure input and output of BX is correct
                    assert parent.cat.semCat.IN.semCatStr == right.cat.semCat.IN.semCatStr
                    assert parent.cat.semCat.OUT.semCatStr == left.cat.semCat.OUT.semCatStr
                    parent.cat.semCat.IN = right.cat.semCat.IN  # assign marking
                    parent.cat.semCat.OUT = left.cat.semCat.OUT  # assign marking
                    # TODO comparator here
                    self.compareSemCat(left.cat.semCat.IN, right.cat.semCat.OUT, parent)
                    # left.cat.semCat.IN = right.cat.semCat.OUT

                # Y/Z X\Y -> X/Z  "DID NOT" is this pattern
                # z-->y  y-->x  ->  z-->x
                else:
                    # make sure input and output of BX is correct
                    # TODO
                    # if parent.cat.semCat.IN and parent.cat.semCat.OUT:
                    try:
                        assert parent.cat.semCat.IN.semCatStr == left.cat.semCat.IN.semCatStr
                        assert parent.cat.semCat.OUT.semCatStr == right.cat.semCat.OUT.semCatStr
                    except AssertionError:
                        eprint('AssertionError in mark, rule = bx')
                        eprint('left:', left.cat.semCat)
                        eprint('right:', right.cat.semCat)
                        eprint('parent:', parent.cat.semCat)
                        raise ErrorCCGtree('error in mark_NTN_myparent')
                    parent.cat.semCat.IN = left.cat.semCat.IN  # assign marking
                    parent.cat.semCat.OUT = right.cat.semCat.OUT  # assign marking

                    # TODO comparator here
                    self.compareSemCat(right.cat.semCat.IN, left.cat.semCat.OUT, parent)
                    # right.cat.semCat.IN = left.cat.semCat.OUT

                # assign marking
                # if at least one of them is None (i.e. dot), result = None:
                if (right.cat.semCat.marking is None) or (left.cat.semCat.marking is None):
                    parent.cat.semCat.marking = None
                elif right.cat.semCat.marking == left.cat.semCat.marking:
                    parent.cat.semCat.marking = '+'
                else:
                    parent.cat.semCat.marking = '-'

            elif parent.ruleType == 'fc':
                # X/Y Y/Z -> X/Z
                if left.cat.right.typeWOfeats == right.cat.left.typeWOfeats:
                    # make sure input and output of fc is correct
                    assert parent.cat.semCat.IN.semCatStr == right.cat.semCat.IN.semCatStr
                    assert parent.cat.semCat.OUT.semCatStr == left.cat.semCat.OUT.semCatStr
                    parent.cat.semCat.IN = right.cat.semCat.IN  # assign marking
                    parent.cat.semCat.OUT = left.cat.semCat.OUT  # assign marking
                    # TODO comparator here
                    self.compareSemCat(left.cat.semCat.IN, right.cat.semCat.OUT, parent)
                    # left.cat.semCat.IN = right.cat.semCat.OUT

                # Y\Z X\Y -> X\Z
                else:
                    assert parent.cat.semCat.IN.semCatStr == left.cat.semCat.IN.semCatStr
                    assert parent.cat.semCat.OUT.semCatStr == right.cat.semCat.OUT.semCatStr
                    parent.cat.semCat.IN = left.cat.semCat.IN  # assign marking
                    parent.cat.semCat.OUT = right.cat.semCat.OUT  # assign marking
                    # TODO comparator here
                    self.compareSemCat(right.cat.semCat.OUT, left.cat.semCat.IN, parent)
                    # right.cat.semCat.OUT = left.cat.semCat.IN

                # assign marking
                # if at least one of them is None (i.e. dot), result = None:
                if (right.cat.semCat.marking is None) or (left.cat.semCat.marking is None):
                    parent.cat.semCat.marking = None
                elif right.cat.semCat.marking == left.cat.semCat.marking:
                    parent.cat.semCat.marking = '+'
                else:
                    parent.cat.semCat.marking = '-'

            elif parent.ruleType in ['rp', 'lp']:
                # rp: right punctuation?
                # punctuation, make parent.marking = non-punctuation-child.marking
                if parent.cat.semCat.semCatStr == left.cat.semCat.semCatStr:
                    parent.cat = left.cat
                else:
                    parent.cat = right.cat

            elif parent.ruleType == 'conj': pass  # already handled

            else:
                eprint('\nunable to process rule in mark_NTN_myparent(): {}'.format(
                    node.parent.ruleType))
                eprint(node)
                eprint(node.parent)
                self.printSent(stream=sys.stderr)
                raise ErrorCCGtree('error in mark_NTN_myparent()')

                # TODO
        else:
            eprint('wrong number of sisters: {}'.format(node))
            raise ErrorCCGtree('error in mark_NTN_myparent()')

        node.parent.visited = True

        # do this every time when we mark a parent
        self.assignEqualMarkingTR()

    # TODO still have to re-traverse the tree for conj

    def mark_NTN_helper_conj(self, node):
        ''' get marking for CONJ rule '''
        if len(node.children) == 0:
            if node.parent.ruleType == 'conj':
                self.mark_NTN_myparent_conj(node)
        else:
            if len(node.children) == 2:  # 2 children
                self.mark_NTN_helper_conj(node.children[0])  # left child
                self.mark_NTN_helper_conj(node.children[1])  # right child
                # now fix node.parent
                if node.parent.ruleType == 'conj':
                    self.mark_NTN_myparent_conj(node)
            elif len(node.children) == 1:  # only one child, rule is either 'lex' or 'tr'
                self.mark_NTN_helper_conj(node.children[0])
                # now fix node itself
                if node.parent.ruleType == 'conj':
                    self.mark_NTN_myparent_conj(node)
            else:
                eprint('number of children more than 2: {}'.format(node))
                raise ErrorCCGtree('error in mark_NTN_myparent()')

    def mark_NTN_myparent_conj(self, node):
        #        conj(conj)=(X\X1)/X2      NP(X2)
        #        -------------------------- conj
        # NP(X1)           NP\NP(parent)=X\X1
        # ----------------------------------- fa/ba
        #             NP(grandparent)=X

        # TODO
        # NOTE: X1 and X2 may have different types!
        # e.g. A man and a woman be in a room paint beige wear dark colored shirt and a monitor be in the background

        parent = node.parent
        conj = parent.children[0]
        X2 = parent.children[1]
        X1 = parent.sisters[0]
        grandparent = parent.parent

        # print("im here!")
        # print(conj.cat.typeWOfeats.upper())

        # first get the cat for conj, and marking on the SLASHES,
        # not on the NP
        # i.e. if right = X, sister = X, then we want conj to be: (X\X)/X
        if conj.cat.typeWOfeats.upper() == 'CONJ':

            # check if X1 type = X2 type
            if X1.cat.typeWOpolarity != X2.cat.typeWOpolarity:
                eprint("bad conjunction! setting conjuction type to 'conj'")
                eprint("\tX1:", X1.cat.typeWOpolarity)
                eprint("\tX2:", X2.cat.typeWOpolarity)
                eprint("\tconj:", conj.cat)
                return

            X2Type = str(X2.cat.typeWOpolarity)

            # if X2Type X is basic: NP, then conj: (NP\NP)/NP
            # but when X2Type is complex: (S\NP)/NP
            # we need an extra pair of brackets for rightType X:
            # i.e. ((X)\(X))/(X) = (((S\NP)/NP)\((S\NP)/NP))/((S\NP)/NP)
            if '(' in X2Type: X2Type = '(' + X2Type + ')'
            elif ('\\' in X2Type) or ('/' in X2Type): X2Type = '(' + X2Type + ')'

            conj.cat = Cat('(' + X2Type + '\\' + X2Type + ')/' +
                           X2Type, word=conj.word)

            # ---------------------------------
            # assign marking to conj, both slashes are '+' TODO
            conj.cat.semCat.marking = '+'
            conj.cat.semCat.OUT.marking = '+'
            # assign marking to parent '+'
            parent.cat.semCat.marking = '+'

            # ---------------------------------
            conj.cat.semCat.IN = X2.cat.semCat
            conj.cat.semCat.OUT.IN = X1.cat.semCat
            parent.cat.semCat.IN = X1.cat.semCat

            # ---------------------------------
            # !! assign parent.OUT marking !! #
            if (X2.cat.typeWOfeats == 'S') and (X1.cat.typeWOfeats == 'S'):
                parent.cat.semCat.marking = '+'  # conjoining two S   S+\S
            elif (X2.cat.semCat.marking is None) or (X1.cat.semCat.marking is None):
                parent.cat.semCat.OUT.marking = None  # this will be grandparent NP
            # if right.marking == sister.marking != None, then grandparent = that marking
            elif X2.cat.semCat.marking == X1.cat.semCat.marking:
                parent.cat.semCat.OUT.marking = X2.cat.semCat.marking
                # assert X1 and X2 are exactly the same
                try: assert X1.cat.semCat.semCatStr == X2.cat.semCat.semCatStr
                except AssertionError:
                    eprint('X1.cat.semCat:', X1.cat.semCat)
                    eprint('X2.cat.semCat:', X2.cat.semCat)
                    raise ErrorCCGtree('error in mark_NTN_myparent_conj')
                parent.cat.semCat.OUT = X2.cat.semCat

            # right and sister have different marking; this handles 'No man but some woman walks'
            else: parent.cat.semCat.OUT.marking = None

            # now set semCat for grandparent
            grandparent.cat.semCat = parent.cat.semCat.OUT

        elif X2.cat.typeWOfeats.upper() == 'CONJ':  # impossible
            raise ErrorCCGtree('right is a conj! this is impossible!')

        # eprint('******')
        # eprint('X2:', X2.cat.semCat)
        # eprint('conj:', conj.cat.semCat)
        # eprint('parent:', parent.cat.semCat)
        # eprint('grandparent:', grandparent.cat.semCat)
        # eprint('******')

    def compareSemCat(self, semCat1, semCat2, parent):
        """
        - traverse semCat1 and semCat2 at the same time,
        - populate the more ``specific'' marking (+/-) to the ``unspecific''
          in each step

        semCat1 > semCat2
        e.g. semCat1 = ((et,-t),((et,t),t))   semCat2 = ((et,t),+((et,t),+t))
        result: ((et,-t),+((et,t),+t))
        [pay attention to +/- signs]
        """

        try: assert semCat1.semCatStr == semCat2.semCatStr  # semCatStr does not have +/-
        except AssertionError: raise ErrorCompareSemCat('parent is: {}'.format(parent))

        # eprint('---\nbefore:\nsemCat1:', semCat1, semCat1.semCatStr)
        # eprint('semCat2:', semCat2, semCat2.semCatStr)

        # recurse through semCat1 and semCat2 at the same time
        self.compareSemCatHelper(semCat1, semCat2, parent)
        # semCat1.marking = semCat2.marking

        # eprint('---\nafter:\nsemCat1:', semCat1, semCat1.semCatStr)
        # eprint('semCat2:', semCat2, semCat2.semCatStr)

    def compareSemCatHelper(self, semCat1, semCat2, parent):
        """ recursive helper function
        e.g. semCat1 = ((et,-t),((et,t),t))   semCat2 = ((et,t),+((et,t),+t))
        result: ((et,-t),+((et,t),+t))
        """
        if semCat1.IN:  # if semCat1.IN is not None
            self.compareSemCatHelper(semCat2.IN, semCat1.IN, parent)
        if semCat1.OUT:
            self.compareSemCatHelper(semCat1.OUT, semCat2.OUT, parent)

        if self.semCatGreater(semCat1, semCat2):  # semCat2 is more specific
            semCat1.marking = semCat2.marking
        else:
            eprint(semCat1, semCat2)
            eprint(semCat1.marking, semCat2.marking)
            eprint("parent: {}".format(parent))
            raise ErrorCompareSemCat("{} not greater than {}\n\n".format(semCat1, semCat2))

    def semCatGreater(self, semCat1, semCat2):
        """ semCat1 >= semCat2 iff: """
        # eprint('compareing: {} and {}'.format(semCat1, semCat2))
        return (semCat1.marking is None) or (semCat1.marking == semCat2.marking)

    def equate_marking(self, semCat1, semCat2):
        """ to assign the same markings on x, y in type (x, y)
        e.g. 1. in negation, didn't = (NP->S)->(NP->S) where both (NP->S) should have
         the same markings
        e.g. 2. verbs of type (NP->S)->(NP->S) as 'manage' in 'I managed to pass the exam'.
        """
        assert semCat1.semCatStr == semCat2.semCatStr
        if self.semCatGreater(semCat1, semCat2):  # OUT is more specific
            semCat1.marking = semCat2.marking
        else: semCat1.marking = semCat2.marking

        # recurse
        if semCat1.IN: self.equate_marking(semCat1.IN, semCat2.IN)
        if semCat1.OUT: self.equate_marking(semCat1.OUT, semCat2.OUT)

    def Krule(self, functor, monoDirection):
        r"""
        if functor.cat.semCat.IN.semCatStr == '((e,t),t)':  # NP
        we look at K-rule
        rule: {'>': fa and ba, 'B': fc and bx}

        # if (S\NP)/NP, then look at markings on both NP
        # if S\NP, then only look at marking on one NP
        """
        NP = functor.cat.semCat.IN
        if NP.marking == '-':     # NP-, flip
            self.polarizeHelper(functor, self.flip(monoDirection))
        elif NP.marking is None:
            if functor.cat.semCat.OUT.semCatStr == '(((e,t),t),t)':
                # (S\NP1)/NP2 TODO is this correct?
                self.polarizeHelper(functor, monoDirection)
            else:                 # NP=
                self.polarizeHelper(functor, 'UNK')
        else:                     # NP+
            self.polarizeHelper(functor, monoDirection)

        # ----------------------------
        # EXPERIMENTAL:
        # if transitive verb: (S\NP)/NP
        # if (functor.cat.semCat.OUT.IN is not None) and \
        #         (functor.cat.semCat.OUT.IN.semCatStr == '((e,t),t)'):
        #     NP2 = functor.cat.semCat.OUT.IN
        #     if (NP.marking is None) or (NP2.marking is None):
        #         self.polarizeHelper(functor, 'UNK')
        #     elif (NP.marking == '+') and (NP2.marking == '+'):  # + +
        #         self.polarizeHelper(functor, monoDirection)
        #     else:  # + -
        #         self.polarizeHelper(functor, self.flip(monoDirection))
        # # intransitive verb: S\NP, or a VP: S/NP
        # else:
        #     if NP.marking == '-':  # NP-, flip
        #         self.polarizeHelper(functor, self.flip(monoDirection))
        #     elif NP.marking is None:  # NP=
        #         self.polarizeHelper(functor, 'UNK')
        #     else:  # NP+
        #         self.polarizeHelper(functor, monoDirection)

    def Krule_composition(self, functor, monoDirection):
        r"""  k-rule for composition
        e.g. in object RC: Z/Y Y/X -> Z/X  i.e. x-->y  y-->z = x-->z
        to expand it:
        x-->y   x
        ----------
            y         y-->z
        --------------------
                z
        If y.IN = NP, then we need to use Krule.
        That is, if y is (NP- --> S), then flip y.
        But it's hard to flip intermediate polarities, so instead,
        we do: if x-->y is '+' on the \rightarrow, and y is NP-, we flip x-->y

        Here x-->y is the functor
        y = functor.cat.semCat.OUT.IN
        """
        if functor.cat.semCat.OUT is not None:
            if functor.cat.semCat.OUT.IN is not None:
                if functor.cat.semCat.OUT.IN.marking == '-':
                    self.polarizeHelper(functor, self.flip(monoDirection))
                elif functor.cat.semCat.OUT.IN.marking is None:
                    self.polarizeHelper(functor, 'UNK')
                else:  # +
                    self.polarizeHelper(functor, monoDirection)
            else:
                self.polarizeHelper(functor, monoDirection)
        else:
            self.polarizeHelper(functor, monoDirection)

    def polarize(self):
        self.polarizeHelper(self.root, 'UP')
        # for leafNode in self.leafNodes:
        #     self.finalFlip(leafNode)

    def polarizeHelper(self, node, monoDirection):
        # assign UP/DOWN to node
        node.cat.monotonicity = monoDirection

        r"""
        # -----------------------
        # TODO new 20181008: no k-rule
        # IN is NP
        if (node.cat.semCat.IN is not None) and \
                (node.cat.semCat.IN.semCatStr == '((e,t),t)'):
            NP = node.cat.semCat.IN
            # if transitive verb: (S\NP)/NP
            if (node.cat.semCat.OUT.IN is not None) and \
                    (node.cat.semCat.OUT.IN.semCatStr == '((e,t),t)'):
                NP2 = node.cat.semCat.OUT.IN
                if (NP.marking is None) or (NP2.marking is None):
                    node.cat.originalType += ' none'
                elif [NP.marking, NP2.marking].count('-') == 1:  # 1 -
                    node.cat.originalType += ' flip'
                else:  # 0 or 2 -
                    pass
            # intransitive verb: S\NP, or a VP: S/NP
            else:
                if NP.marking == '-':  # NP-, flip
                    node.cat.originalType += ' flip'
                elif NP.marking is None:  # NP=
                    node.cat.originalType += ' none'
                else:  # NP+
                    pass
        # -----------------------
        """

        if len(node.children) == 0:  # leaf
            return
        if len(node.children) == 2:  # 2 children
            left = node.children[0]
            right = node.children[1]

            if node.ruleType == 'ba':  # Y X\Y --> X   functor = right
                try:
                    if right.ruleType.upper() == 'CONJ':
                        self.polarizeHelper(left, self.calcMono(right, monoDirection))
                        self.polarizeHelper(right, monoDirection)
                    else:
                        if right.cat.semCat.IN.semCatStr == '((e,t),t)':  # NP
                            self.Krule(right, monoDirection)  # k rule
                        else:
                            self.polarizeHelper(right, monoDirection)
                        self.polarizeHelper(left, self.calcMono(right, monoDirection))
                except AttributeError:  # 'LeafNode' (right) object has no attribute 'ruleType'
                    if right.cat.semCat.IN.semCatStr == '((e,t),t)':  # NP
                        self.Krule(right, monoDirection)  # k rule
                    else:
                        self.polarizeHelper(right, monoDirection)
                    self.polarizeHelper(left, self.calcMono(right, monoDirection))

            elif node.ruleType == 'fa':  # X/Y Y --> X   functor = left
                try:
                    if left.ruleType.upper() == 'CONJ':
                        self.polarizeHelper(right, self.calcMono(left, monoDirection))
                        self.polarizeHelper(left, monoDirection)
                    else:
                        if left.cat.semCat.IN.semCatStr == '((e,t),t)':  # NP
                            self.Krule(left, monoDirection)  # k rule
                        else:
                            self.polarizeHelper(left, monoDirection)
                        self.polarizeHelper(right, self.calcMono(left, monoDirection))
                except AttributeError:  # 'LeafNode' (left) object has no attribute 'ruleType'
                    if left.cat.semCat.IN.semCatStr == '((e,t),t)':  # NP
                        self.Krule(left, monoDirection)  # k rule
                    else:
                        self.polarizeHelper(left, monoDirection)
                    self.polarizeHelper(right, self.calcMono(left, monoDirection))

            elif node.ruleType == 'bx':
                # X/Y Y\Z -> X\Z    functor = left
                if node.cat.direction == 'l':
                    if (len(left.children) != 0) and \
                            (left.cat.semCat.IN.semCatStr == '((e,t),t)'):  # NP
                        self.Krule(left, monoDirection)  # TODO no k rule if leafNode
                    else:
                        self.polarizeHelper(left, monoDirection)
                    self.polarizeHelper(right, self.calcMono(left, monoDirection))
                # Y/Z X\Y -> X/Z    functor = right
                else:
                    if (len(right.children) != 0) and \
                            (right.cat.semCat.IN.semCatStr == '((e,t),t)'):  # NP
                        self.Krule(right, monoDirection)  # TODO no k rule if leafNode
                    else:
                        self.polarizeHelper(right, monoDirection)
                    self.polarizeHelper(left, self.calcMono(right, monoDirection))

            elif node.ruleType == 'fc':  # Z/Y Y/X -> Z/X or Y\X Z\Y -> Z\X
                # X/Y Y/Z -> X/Z    functor = left
                if node.cat.direction == 'r':
                    if (len(left.children) != 0) and \
                            (left.cat.semCat.IN.semCatStr == '((e,t),t)'):  # NP
                        self.Krule(left, monoDirection)  # TODO no k rule if leafNode
                    else:
                        self.polarizeHelper(left, monoDirection)
                    self.polarizeHelper(right, self.calcMono(right, monoDirection))
                # Y\Z X\Y -> X\Z    functor = right
                else:
                    if (len(right.children) != 0) and \
                            (right.cat.semCat.IN.semCatStr == '((e,t),t)'):  # NP
                        self.Krule(right, monoDirection)  # TODO no k rule if leafNode
                    else:
                        self.polarizeHelper(right, monoDirection)
                    self.polarizeHelper(left, self.calcMono(right, monoDirection))

            elif node.ruleType == 'conj':  # conjunction
                try:  #
                    if left.cat.typeWOfeats == "conj":
                        eprint("unable to polarize conj rule! X1, X2 not same type!")
                    elif left.pos.upper() == 'CC':
                        #        conj(left)      NP(right)
                        #        -------------------------- conj
                        # NP(sister)           NP\NP(parent)
                        # ----------------------------------- fa/ba
                        #             NP
                        # right.mono = sister.mono
                        self.polarizeHelper(right, right.parent.sisters[0].cat.monotonicity)
                        left.cat.monotonicity = 'UP'  # set the conj to UP, no matter what
                except AttributeError:  # 'NonTermNode' object has no attribute 'pos'
                    try:
                        if right.pos.upper() == 'CC':
                            self.polarizeHelper(left, left.parent.sisters[0].cat.monotonicity)
                            right.cat.monotonicity = 'UP'  # set the conj to UP, no matter what
                    except AttributeError:
                        eprint('unable to polarize conj rule!\nNo "CC" pos')
                except:
                    eprint('unable to polarize conj rule!\n')
                    eprint(left)
                    eprint(right)
                    raise ErrorCCGtree('unable to polarize conj rule!')
            elif node.ruleType in ['rp', 'lp']: # punctuation
                self.polarizeHelper(left, monoDirection)
                self.polarizeHelper(right, monoDirection)
            else:
                raise ErrorCCGtree('unknown ruleType in polarize: '
                                   '{}'.format(node.ruleType))

        elif len(node.children) == 1:  # 1 child
            child = node.children[0]
            if node.ruleType == 'lex':
                self.polarizeHelper(child, monoDirection)
            elif node.ruleType == 'unlex':  # keep the same direction
                self.polarizeHelper(child, monoDirection)
            elif node.ruleType == 'tr':  # type raising
                # for (x->y)->y, the +/- on the first (i.e. left) arrow
                # determines the monoDirection of child
                self.polarizeHelper(child,
                                    self.calcMono(node.cat.semCat.IN.marking,
                                                  monoDirection))
            else:
                eprint('unknown ruleType in polarize: {}'.format(node.ruleType))
                pass

    def calcMono(self, functorORmarking, monoDirection):
        ''' functorORmarking can either be a functor or simply marking(+/-) '''
        marking = functorORmarking
        if functorORmarking not in ['-', '+', None]:
            marking = functorORmarking.cat.semCat.marking

        if monoDirection == 'UP' and marking == '-':
            return 'DOWN'
        elif monoDirection == 'DOWN' and marking == '-':
            return 'UP'
        elif monoDirection == 'UP' and marking == '+':
            return 'UP'
        elif monoDirection == 'DOWN' and marking == '+':
            return 'DOWN'
        elif monoDirection == 'UNK' or marking is None:  # None = 'dot':
            return 'UNK'
        else:
            self.printTree()
            eprint(marking, monoDirection)
            raise ErrorCCGtree('Unknown Mono monoDirection/functor!')

    def flip(self, monoDirection):
        ''' flip UP and DOWN'''
        if monoDirection == 'UP': return 'DOWN'
        elif monoDirection == 'DOWN': return 'UP'
        else: return 'UNK'

    def finalFlip(self, leafNode):
        r''' if the leafNode is a verb: S\NP, or (S\NP)/NP, then check the
        number of NP-. If there are odd number of NP-, flip its polarity '''
        if leafNode.cat.typeWOfeats == r'S\NP':  # intransitive verb
            if leafNode.cat.semCat.IN.marking == '-':
                leafNode.cat.monotonicity = self.flip(leafNode.cat.monotonicity)
        elif leafNode.cat.typeWOfeats == r'(S\NP)/NP':  # transitive verb
            marking_outer_NP = leafNode.cat.semCat.IN.marking
            marking_inner_NP = leafNode.cat.semCat.OUT.IN.marking
            # if one is - and the other is +, then flip
            if ((marking_outer_NP == '-') and (marking_inner_NP == '+')) or \
                    ((marking_outer_NP == '+') and (marking_inner_NP == '-')):
                leafNode.cat.monotonicity = self.flip(leafNode.cat.monotonicity)

    def getImpSign(self):
        """ propagate the implicative sign from root to leaf
        my algorithm:
        * root has default +.
        * Whenever one of the two child nodes has
        impType, need to compute the impSign of the other child,
        based on the impType
        """
        self.root.impSign = "+"
        self.getImpSignHelper(self.root)

    def getImpSignHelper(self, node):
        """ node is the parent """
        if len(node.children) == 0: return
        if len(node.children) == 1:
            node.children[0].impSign = node.impSign
            self.getImpSignHelper(node.children[0])
        else:  # 2 children
            # find out if any child has impType
            functor, argument = None, None
            # if len(node.children[0].children) == 0:
            #     if node.children[0].word in {"not", "n't"}:
            #         eprint(node.children[0])
            #         eprint(node.children[0].impType.impType_str)
            if node.children[0].impType.impType_str:  # children[0] has impType
                functor = node.children[0]
                argument = node.children[1]
            if node.children[1].impType.impType_str:  # children[1] has impType
                functor = node.children[1]
                argument = node.children[0]

            if functor:  # if one child has impType
                functor.impSign = node.impSign
                argument.impSign = self.computeImpSign(functor)
                # eprint(functor)  # should be a implivative verb
            else:  # just propagate up
                node.children[0].impSign = node.impSign
                node.children[1].impSign = node.impSign
            self.getImpSignHelper(node.children[0])
            self.getImpSignHelper(node.children[1])

    def computeImpSign(self, functor):
        """ if functor = forget +-|-+, then return the flipped impSign """
        if functor.impSign == "-":
            if "nn" in functor.impType.impType_str: return "-"
            if "np" in functor.impType.impType_str: return "+"
            else: return "\u2022"  # bullet
        elif functor.impSign == "+":
            if "pp" in functor.impType.impType_str: return "+"
            if "pn" in functor.impType.impType_str: return "-"
            else: return "\u2022"  # bullet
        elif functor.impSign == "\u2022":
            return "\u2022"

    def build_easyccg(self, easyccg_tree_str, changes_onetree=None):
        ''' build the tree recursively from easyccg extended output string '''

        # the boundaries of nodes are marked by { and }, not ( or ), nor [ or ]
        # make sure there are same number of { and }
        try: assert easyccg_tree_str.count('{') == easyccg_tree_str.count('}')
        except AssertionError:
            eprint('unequal num of { and }\n#{: %s, #}: %s' %
                  (easyccg_tree_str.count('{'),
                  easyccg_tree_str.count('}')))
            eprint(easyccg_tree_str)
            raise ErrorCCGtree("Error in build_easyccg()")

        def findIdxStr(s, char_set):
            ''' find all index of char in string s
            char_set is the set of characters we want to find
            return a list '''
            return [i for i, ch in enumerate(s) if ch in char_set]

        def getBrk(idx, easyccg_tree_str, idxBrk):
            ''' return the Brk, (< or >), based on idx of curr Brk '''
            return easyccg_tree_str[idxBrk[idx]]

        # don't need dummy root if reading from easyccg!
        # self.root = NonTermNode(depth=-1)

        # print(easyccg_tree_str)

        # find idx of ( and )
        idxBrk = findIdxStr(easyccg_tree_str, {'{', '}'})
        # print(idxBrk)

        numBrk = len(idxBrk)
        numLeafNode = 0
        numNTN = 0
        i = 0
        stack = []

        while i < numBrk - 1:
            currBrk = getBrk(i, easyccg_tree_str, idxBrk)
            nextBrk = getBrk(i+1, easyccg_tree_str, idxBrk)
            # print('\ncurr Brk', currBrk)
            # print('next Brk', nextBrk)

            # leaf node:
            # <L N John John NNP I-PER O N>
            # <L ((S[dcl]\NP)/PP)/NP puts put VBZ O O ((S[dcl]\NP)/PP)/NP>
            # Leaf - category - token - lemma - pos - NER - chunk - category?

            # non term node:
            # <T S[dcl]\NP fa 0 2>
            # NTN - category - rule - start - end/span??

            # start of leaf node
            if (currBrk == '{') and (nextBrk == '}'):
                numLeafNode += 1
                node_str = easyccg_tree_str[ (idxBrk[i]+2) : (idxBrk[i+1]-1) ]
                # print(node_str)
                node_lst = node_str.split(' ')
                try:
                    if len(node_lst) == 6:  # CCGbank ['L', 'N/N', 'NNP', 'NNP', 'Pierre', 'N_73/N_73']
                        category_str, token = node_lst[1], node_lst[4]
                        lemma = None; pos = None; NER = None; chunk = None
                    else:
                        category_str, token, lemma, pos, NER, chunk = \
                        node_lst[1], node_lst[2], node_lst[3], node_lst[4], node_lst[5], node_lst[6]
                except IndexError:
                    eprint('node_str index error: {}'.format(node_str))
                    raise ErrorCCGtree("Error in build_easyccg()")

                cat = Cat(originalType=category_str, word=token)
                lf_node = LeafNode(depth=0, cat=cat, chunk=chunk, entity=NER,
                                   lemma=lemma, pos=pos, span=1,
                                   start=numLeafNode-1, word=token)
                # print(lf_node)
                self.words.append(lf_node.word.upper())

                # add lf_node to the last ntn_node in stack
                ntn_node = stack[-1]
                lf_node.parent = ntn_node  # set parent pointer
                if len(ntn_node.children) == 1:  # ntn_node already has a child, set sister
                    sister = ntn_node.children[0]
                    lf_node.sisters = [sister]
                    sister.sisters = [lf_node]
                ntn_node.children.append(lf_node)

                self.leafNodes.append(lf_node)  # append to self.leafNodes
                i += 2

            # start of NT node
            elif (currBrk == '{') and (nextBrk == '{'):
                node_str = easyccg_tree_str[ (idxBrk[i]+2) : (idxBrk[i+1]-2) ]
                # print(node_str)
                node_lst = node_str.split(' ')
                try:
                    if len(node_lst) == 4:  # output from CCGbank
                        category_str, start, end = \
                        node_lst[1], node_lst[2], node_lst[3]
                        rule = None
                    else:
                        category_str, rule, start, end = \
                        node_lst[1], node_lst[2], node_lst[3], node_lst[4]
                except IndexError:
                    eprint('node_str index error: {}'.format(node_str))
                    raise ErrorCCGtree("Error in build_easyccg()")

                cat = Cat(originalType=category_str)
                ntn_node = NonTermNode(depth=0, cat=cat, ruleType=rule)
                # if rule == "bx":
                    # eprint(ntn_node)
                    # eprint(ntn_node.cat.semCat)
                    # eprint(ntn_node.cat.semCat.IN)
                    # eprint(ntn_node.cat.semCat.OUT)
                    # eprint()
                    # exit()
                stack.append(ntn_node)
                numNTN += 1
                i += 1

            # end of NT node, pop a node
            else:  # (currBrk == '}')
                node_popped = stack.pop(-1)
                # print('*** length of stack ***: {}'.format(len(stack)))

                # if the stack is not empty,
                # then ntn_node is one child of the current last node in stack
                if len(stack) != 0:
                    last_node = stack[-1]
                    node_popped.parent = last_node  # set parent pointer
                    if len(last_node.children) == 1:  # last_node already has a child, set sister
                        sister = last_node.children[0]
                        node_popped.sisters = [sister]
                        sister.sisters = [node_popped]
                    last_node.children.append(node_popped)
                else: pass # nothing in stack; this never happens

                self.nonTermNodes.append(node_popped)
                # TODO get wholeStr of ntn_node
                i += 1

        # print('\n\n')
        # print('leaf:', numLeafNode)
        # print('NTN:', numNTN)

        # there is one last node in stack, pop it and attach it to dummy root
        assert len(stack) == 1
        last_node = stack.pop(-1)
        self.root = last_node
        self.regetDepth()

        dummy_root = NonTermNode(depth=-1)  # dummy root, as the parent of real self.root
        dummy_root.children = [self.root]
        self.root.parent = dummy_root

        # self.printTree()
        self.getWholeStrAllNodes()
        self.wholeStr = self.root.wholeStr
        # allNodes
        self.allNodes = self.leafNodes + self.nonTermNodes

        if changes_onetree: self.recover_tree(changes_onetree)

    def recover_tree(self, changes_onetree):
        ''' recover tree from changes: e.g. no => at most 5 '''
        # changes_onetree is a list of changes
        # [ {'before':at most 5, 'after':no, 'idx':0}, {} ... ]
        eprint('changes:')
        eprint(changes_onetree)
        changes = changes_onetree

        for change in changes:
            # check whether it's `at most' or `at least' or `a-lot-of'
            if change['after'].upper() == "NO":
                self.recover_at_most_least("at-most", change)
            elif change['after'].upper() == "SOME":
                self.recover_at_most_least("at-least", change)
            elif change['before'] == "a-lot-of":
                self.recover_a_lot_of()  # TODO
            else:
                eprint("something wrong in changes for sentence:")
                self.printSent()
                return

    def recover_at_most_least(self, quant, changes):
        """ recover 'at most' and 'at leat' """
        idx = -1
        counter = 0

        # step 1. how many 'no' are there in tree
        for i, lnode in enumerate(self.leafNodes):
            if lnode.word.upper() == changes['after'].upper():
                idx = i
                counter += 1

        if counter > 1:
            eprint("cannot handle two 'at-most/least' changes in one sentence")
            return
        elif counter == 0:
            eprint("something wrong in changes for sentence:")
            self.printSent()
            return
        else:
            node_old = self.leafNodes[idx]  # !!! replace this with `at most 5'

        # step 2. build 'at-most 5'
        #   at-most          5               let's say numbers are of type N/N
        #   (NP/N)/(N/N)     N/N
        #   ---------------------- fa        people
        #            NP/N                      N
        # TODO lemma, word?
        node_at_most = LeafNode(depth=0, cat=Cat(originalType="(NP/N)/(N/N)",
                                                    word=quant),
                                chunk=None, entity=None,
                                lemma=quant, pos="DT", span=None, start=None,
                                word=quant, impType=None, fixed=True,
                                note=quant)
        # quant = at-most or at-least

        num_str = changes['before'].split()[-1]
        node_num = LeafNode(depth=0, cat=Cat(originalType="N/N",
                                                    word=num_str),
                                chunk=None, entity=None,
                                lemma=num_str, pos="CD", span=None, start=None,
                                word=num_str, impType=None, fixed=True)

        node_at_most_num = NonTermNode(depth=0, cat=Cat(originalType="NP/N"),
                                       ruleType="fa", note=quant+'-N')
        node_at_most_num.children = [node_at_most, node_num]
        node_at_most.parent, node_num.parent = node_at_most_num, node_at_most_num

        # step 3. replace `no' with `at most 5'    kEY STEP!!
        node_old.parent.children[0] = node_at_most_num
        node_at_most_num.parent = node_old.parent

        # step 4. rebuld tree
        self.buildFromRoot()

        # self.printSent()
        # self.printTree()

    def recover_a_lot_of(self):
        """ recover. Change 'much' to 'a lot of' """
        # step 1: find the node 'much'
        for lnode in self.leafNodes:
            if lnode.word == 'much':
                # step 2: replace it with 'a lot of'
                node_a_lot_of = LeafNode(depth=0,
                                         cat=Cat(originalType=lnode.cat.typeWOfeats, word='a-lot-of'),
                                         chunk=None,entity=None,lemma='a-lot-of',
                                         pos=lnode.pos,span=0,start=0,
                                         word='a-lot-of',impType=None,fixed=False,
                                         note="a-lot-of")
                # get idx of 'much'
                idx = lnode.parent.children.index(lnode)
                lnode.parent.children[idx] = node_a_lot_of
                node_a_lot_of.parent = lnode.parent
                lnode.parent = None

        self.buildFromRoot()

    def build_CandC(self, ccgXml, changes_onetree=None):
        ''' build the tree recursively from xml output of CandC '''
        self.root = NonTermNode(depth=-1)  # dummy root; important for building the tree from candc
        self.build_CandC_helper(ccgXml, self.root, -1)
        self.getWholeStrAllNodes()
        # allNodes
        self.allNodes = self.leafNodes + self.nonTermNodes
        # self.printTree()
        if changes_onetree: self.recover_tree(changes_onetree)

    def build_CandC_helper(self, nodeXml, Node, depth):
        for childXml in nodeXml.find_all(re.compile('(lf|rule)'), recursive=False):
            if childXml.find('lf') is None:  # if the child is leaf
                cat = Cat(**{'originalType':childXml['cat'], 'word':childXml['word']})
                leafNode = LeafNode(depth=depth+1, cat=cat, chunk=childXml['chunk'],
                                    entity=childXml['entity'], lemma=childXml['lemma'],
                                    pos=childXml['pos'], span=childXml['span'],
                                    start=childXml['start'], word=childXml['word'])
                Node.children.append(leafNode)
                leafNode.parent = Node
                leafNode.impType = ImpType(childXml['lemma'], childXml['pos'])
                self.leafNodes.append(leafNode)
                self.words.append(leafNode.word.upper())
            else:  # non terminal node
                cat = Cat(childXml['cat'])
                childNode = NonTermNode(depth+1, cat, childXml['type'])
                Node.children.append(childNode)
                childNode.parent = Node
                self.build_CandC_helper(childXml,childNode,depth+1)

        # add sisters
        for childNode in Node.children:
            sisters = Node.children.copy()
            sisters.remove(childNode)
            childNode.sisters = sisters
        if Node.depth != -1: # to exclude the dummy None root
            self.nonTermNodes.append(Node)
        else:  # the dummy root. The real root should be its only child
            assert len(Node.children) == 1
            self.root = Node.children[0]

    def fixQuantifier(self):
        if not any([ quant in self.words for quant in QUANTIFIERS_TO_FIX ]):
            return
        flag = self.fixQuantifierHelper()
        while flag: flag = self.fixQuantifierHelper()

    def fixQuantifierHelper(self):
        """ fix the cat of some quantifiers and the tree structure
        return False if there are no more quantifiers to fix
        - QUANTIFIERS_TO_FIX:
        'MOST', 'MANY', 'FEW', 'SEVERAL', 'ONE'
        """
        # first identify the quantifier to fix
        quant = None
        for lfnode in self.leafNodes:
            if lfnode.fixed: continue  # already fixed!
            if lfnode.wholeStr in QUANTIFIERS_TO_FIX:
                if lfnode.cat.typeWOfeats == r"N/N" and lfnode.parent.ruleType == "fa":
                    # only fix quant if N/N, when NP/N, don't fix it
                    quant = lfnode.wholeStr
                    # eprint(quant)
                    break
        if quant is None: return False  # everything fixed!!

        # check if it's ``at most''
        nodeMost = None
        nodeMostID = None
        for i in range(len(self.leafNodes)):
            if i == 0:
                if self.leafNodes[i].word.upper() == quant and \
                        self.leafNodes[i].cat.typeWOfeats == r"N/N":
                    nodeMost = self.leafNodes[i]
                    nodeMostID = 0
            else:
                if self.leafNodes[i].word.upper() == quant and \
                        self.leafNodes[i].cat.typeWOfeats == r"N/N":
                    # make sure the word before it is not 'AT', 'A', at most, a few
                    if self.leafNodes[i-1].word.upper() in {'AT', 'A', 'LEAST'}:
                        self.leafNodes[i].fixed = True
                    else :  # it's not at most, a few; needs fixing
                        nodeMost = self.leafNodes[i]
                        nodeMostID = i
                else: continue

        # the following works when there is no RC: most people are ...
        flag_RC = False
        if nodeMost:
            if nodeMost.parent.sisters:
                if nodeMost.parent.sisters[0].children:
                    if hasattr(nodeMost.parent.sisters[0].children[0], 'word'):
                        if nodeMost.parent.sisters[0].children[0].word.upper() in {"WHO","WHICH","THAT"}:
                            flag_RC = True

        if not flag_RC:  # no RC
            if nodeMost:   # fix trees involving 'most'
                # BEFORE:
                #   most    dogs
                #    N/N      N  <= nodeMostSister
                # fa--------------
                #          N  <= nodeN
                # lex-------------
                #          NP  <= nodeNP

                # AFTER:
                #   most NP/N     dogs N
                # fa----------------------
                #              NP
                nodeN = nodeMost.parent
                nodeNP = nodeN.parent
                try:
                    nodeMostSister = nodeMost.sisters[0]
                except IndexError:
                    return False  # consider it as fixed

                # get new nodeMost
                nodeMostNew = LeafNode(depth=nodeMost.depth-1, cat=Cat('NP/N', quant.lower()),
                                       chunk=nodeMost.chunk, entity=nodeMost.entity,
                                       lemma=nodeMost.lemma, pos='DT',
                                       span=nodeMost.span, start=nodeMost.start,
                                       word=nodeMost.word, impType=None, fixed=True)
                # nodeMostNew.cat.semCat.OUT.marking = '+'
                # nodeMostNew.cat.semCat.marking = None
                # nodeMostNew.sisters = [nodeMostSister]
                nodeMostNew.parent = nodeNP

                # fix nodeMostSister, and its depth
                nodeMostSister.parent = nodeNP
                # self.decreaseDepth(nodeMostSister)

                # fix nodeNP
                nodeNP.ruleType = 'fa'
                nodeNP.children = [nodeMostNew, nodeMostSister]

                # fix self.leafNodes
                # self.leafNodes[nodeMostID] = nodeMostNew

                # rebuild tree
                self.buildFromRoot()

                return True

            else:  # nodeMost = None, i.e. it's "AT MOST", or no 'most' in sent
                return True
        else:
            # ---------------------------------
            # there is RC

            # before:  (from easyccg)
            # most    Europeans         who          VP
            # N/N         N = node_N    (N\N)/(S\NP)    S\NP
            # ---------------           ---------------------
            #        N                    N\N  =  node_1
            #       --------------------------
            #                   N
            #         ------------------- lex
            #                  NP  =  node_NP

            # after:
            #                         who          VP
            #                      (N\N)/(S\NP)    S\NP
            #          Europeans  ---------------------
            #              N            N\N  =  node_1
            #   most     ------------------ba
            #   NP/N              N  =  node_2
            #  ----------------------fa
            #              NP   =  node_NP
            if nodeMost:
                eprint('\nfixing\n\tmost/many/several + N + RC')
                node_most_new = LeafNode(depth=0, cat=Cat('NP/N', word=quant.lower()),
                                             chunk=None, entity=None,
                                             lemma=nodeMost.lemma, pos='DT', span=None, start=None,
                                             word=nodeMost.word, impType=None, fixed=True)
                node_N = nodeMost.sisters[0]
                node_1 = nodeMost.parent.sisters[0]
                node_NP = nodeMost.parent.parent.parent

                # something wrong, cannot fix it
                if node_NP.cat.typeWOfeats != 'NP':
                    eprint('something wrong fixing most + N + RC; cannot fix it')
                    nodeMost.fixed = True
                    return True

                # combine node_N and node_1
                node_2 = NonTermNode(depth=0, cat=Cat('N'), ruleType='ba')
                node_2.children = [node_N, node_1]
                node_N.parent, node_1.parent = node_2, node_2

                node_NP.ruleType = 'fa'
                node_NP.children = [node_most_new, node_2]
                node_most_new.parent, node_2.parent = node_NP, node_NP

                self.buildFromRoot()
                return True

            else:  # nodeMost = None, i.e. it's "AT MOST", or no 'most' in sent
                return True

    def fixRC(self):
        RelPronouns = ['WHO', 'WHOM', 'THAT', 'WHICH']
        if not any(x in self.words for x in RelPronouns):
            return # does not have RC
        # -----------------------------
        # fix trees involving Relative Clauses
        # -----------------------------

        # -----------------------------
        # we can only handle:
        # **no/some/every/most young man** that every woman hits
        # -----------------------------

        # BEFORE:
        # (COULD BE Object RC, or Subject RC)
        # no             young man         that            every woman hits OR eats pizzas
        # NP/N <= nodeQ  N <= nodeN         (NP\NP)/(S\/NP)       S/NP or S\NP
        # -----------------              ---------------------------------
        #       NP  <= nodeFakeNP        NP\NP  <= nodeRC
        #       -----------------------------------------
        #                      NP  <= nodeTrueNP

        # AFTER:
        #                      that            every woman hits OR eats pizzas
        #       young man      (NP\NP)/(S\/NP)       S/NP or S\NP
        #       ---------     ----------------------------------
        #          N <= nodeN            NP\NP  <= nodeRC
        #         --------- lex
        #  no          NP <= nodeNewNP1 (lex rule is one rule in C&C)
        # ----         ---------------------------------- ba
        #  NP/N <= nodeQ                NP <= nodeNewNP2
        #                           ---------------------- unlex
        #                                  N <= nodeNtmp
        #          TODO: both should be functor:
        #          TODO: one is quantifier, the other is NP
        #          TODO: for now I will change NP to N
        #  --------------------------------------- fa
        #                NP  <= nodeTrueNP

        numNonTermNodes_before = len(self.nonTermNodes)

        # test if the first word in the preceeding NP is a quantifier
        for node in self.nonTermNodes:
            if node.cat.typeWOfeats == r'NP\NP':
                nodeRC = node
                leftMostWordRC = self.getLeftMostLeaf(nodeRC)
                # print("the leftmost word of potential RC is:", leftMostWordRC.word)

                if leftMostWordRC.word.upper() in RelPronouns:
                    # this is RC
                    nodeTrueNP = nodeRC.parent
                    # left most word of preceeding noun
                    leftMostWordPreN = self.getLeftMostLeaf(nodeTrueNP)
                    # print('leftMostWordPreN.word:',leftMostWordPreN.word)
                    if leftMostWordPreN.word.upper() in [
                        'NO', 'SOME', 'EVERY', 'MOST', 'ANY', 'ALL',
                        'EACH', 'THE']:
                        # quantifier
                        nodeFakeNP = nodeTrueNP.children[0]
                        assert nodeFakeNP.children[0] == leftMostWordPreN
                        nodeN = nodeFakeNP.children[1]
                        nodeQ = nodeFakeNP.children[0]

                        # ----- real work starts here ----- #
                        # add lex rule to make nodeN to NP (nodeNewNP1)
                        nodeNewNP1 = NonTermNode(depth=0, cat=Cat('NP'),
                                                 ruleType='lex')
                        nodeN.parent = nodeNewNP1
                        nodeNewNP1.children.append(nodeN)
                        nodeN.sisters = []
                        nodeNewNP1.sisters = [nodeRC]
                        nodeRC.sisters = [nodeNewNP1]

                        # nodeNewNP1 + nodeRC = nodeNewNP2 (ba rule)
                        nodeNewNP2 = NonTermNode(depth=0, cat=Cat('NP'),
                                                 ruleType='ba')
                        nodeNewNP2.children.append(nodeNewNP1)
                        nodeNewNP2.children.append(nodeRC)
                        nodeNewNP1.parent = nodeNewNP2
                        nodeRC.parent = nodeNewNP2
                        nodeNewNP2.sisters = []

                        # nodeNewNP2 -> nodeNtmp, unlex rule
                        nodeNtmp = NonTermNode(depth=0, cat=Cat('N'),
                                                 ruleType='unlex')
                        nodeNtmp.children.append(nodeNewNP2)
                        nodeNewNP2.parent = nodeNtmp
                        nodeNtmp.sisters = [nodeQ]
                        nodeQ.sisters = [nodeNtmp]

                        # nodeQ + nodeNtmp = nodeTrueNP
                        nodeTrueNP.children = [nodeQ, nodeNtmp]
                        nodeQ.parent = nodeTrueNP
                        nodeNtmp.parent = nodeTrueNP
                        nodeTrueNP.ruleType = 'fa'

                        # fix self.nonTermNodes
                        try:
                            self.nonTermNodes.remove(nodeFakeNP)
                            self.nonTermNodes.append(nodeNewNP1)
                            self.nonTermNodes.append(nodeNewNP2)
                            self.nonTermNodes.append(nodeNtmp)
                        except ValueError:
                            eprint('error removing node from nonTermNodes')
                            pass

                        # sanity check: after the fix, 2 more NonTermNodes for each RC
                        # could have multiple RCs
                        numNonTermNodes_after = len(self.nonTermNodes)
                        assert (numNonTermNodes_before - numNonTermNodes_after) % 2 == 0

                        # recalculate depth
                        self.regetDepth()
                        # ----- real work ends here ----- #
                else:
                    continue

        # print('fixing RC done!\n')
        pass

    def fixNot(self):
        r"""
        fix: did not, do not, does not
        BEFORE:
             did               not
        (S\NP)/(S\NP)      (S\NP)\(S\NP)
        bx--------------------------------            sleep
                (S\NP)/(S\NP) <- node_did_not       S\NP  <- node_VP
                fa--------------------------------------
                             S\NP  <- node_whole_VP

        AFTER:
                             not **change cat**      sleep
                         (S\NP)/(S\NP)               S\NP
            did         fa--------------------------------
        (S\NP)/(S\NP)              S\NP  <- node_new
        fa---------------------------------
                         S\NP   <- node_whole_VP
        """
        if ("NOT" not in self.words) and ("N'T" not in self.words): return
        # find node_not
        node_not_s = []  # may have multiple "did not"
        for lfnode in self.leafNodes:
            if lfnode.word.lower() in {"not", "n't"}:
                if lfnode.parent.children[0].word.lower() \
                        in {"do", "does", "did", "is"}:  # TODO "is" ok here?
                    if lfnode.cat.typeWOpolarity == r"(S\NP)\(S\NP)":
                        node_not_s.append(lfnode)
        for node_not in node_not_s:
            # name other nodes
            node_did = node_not.parent.children[0]
            node_did_not = node_not.parent
            node_VP = node_did_not.sisters[0]
            node_whole_VP = node_did_not.parent

            # check node_VP.cat = S\NP
            if node_VP.cat.typeWOfeats != r"S\NP":
                eprint("warning: something weird in fixNot()")
                continue  # then don't fix this 'not'

            # make a new node_not, could be NOT or N'T
            cat = Cat(originalType=r"(S\NP)/(S\NP)",word=node_not.word)
            impType = ImpType(lemma=node_not.lemma, pos=node_not.pos)
            node_not = LeafNode(depth=0,cat=cat,chunk="I-VP",entity="O",
                                lemma=node_not.lemma,pos="RB",span="1",
                                start=node_not.start,word=node_not.word,
                                impType=impType)

            # fix it
            cat = Cat(originalType=r"S\NP", word=None)
            node_new = NonTermNode(depth=0, cat=cat, ruleType="fa", wholeStr="")
            # fix parent children pointer
            node_new.children = [node_not, node_VP]
            node_new.parent = node_whole_VP

            node_VP.parent = node_new
            node_not.parent = node_new
            node_did.parent = node_whole_VP

            node_whole_VP.children = [node_did, node_new]
            self.buildFromRoot()

    def regetDepth(self):
        ''' calculate depth again, just need to traverse the tree '''
        self.regetDepthHelper(self.root, 0)

    def regetDepthHelper(self, node, depth):
        node.depth = depth
        if len(node.children) == 0:
            return
        for child in node.children:
            self.regetDepthHelper(child, depth+1)

    def getLeftMostLeaf(self, node):
        ''' return the left most leaf of all the nodes under node
        X    Y        Z
        ------
           A
           -------------
                 B
        getLeftMostLeaf(B) will return X
        '''
        while len(node.children) != 0:
            node = node.children[0]
        return node

    def decreaseDepth(self, node):
        node.depth -= 1
        if len(node.children) == 0: return
        else:
            for n in node.children: self.decreaseDepth(n)

    def getSubjPredISA(self):
        '''
        find the subject and predicate in ISA sentence
        e.g. Tom Hanks is a cat.  # next step: Tom Hanks is a cute cat.
        returns: [Tom Hanks, cat]
        '''
        ISnode = None
        for n in self.leafNodes:
            if n.wholeStr.upper() == "IS":
                ISnode = n
                break
        # print(ISnode)
        if ISnode is not None:
            # subj is ISnode.parent.sisters[0]; pred is ISnode.sisters[0].children[1]
            subj = ISnode.parent.sisters[0]
            pred = ISnode.sisters[0].children[1]
            return (subj, pred)
        else:
            return (None, None)

class LeafNode:
    def __init__(self,depth,cat,chunk,entity,lemma,pos,span,start,word,impType=None,fixed=False,note=None):
        self.parent = None; self.children = []; self.sisters = []
        self.depth = depth

        self.cat = cat; self.chunk = chunk; self.entity = entity
        self.lemma = lemma; self.pos = pos; self.span = span
        self.start = start
        # --------------
        # self.word = word
        # self.wholeStr = word.upper()
        self.word = lemma
        self.wholeStr = lemma.upper()
        self.word_raw = word
        # --------------
        self.visited = True  # whether visited or not when assigning plus/minus sign
        self.span_id = None  # an id, for mytree2transccg.py
        if impType is None: self.impType = ImpType()
        else: self.impType = impType  # type of implicative
        self.impSign = None  # sign of implicative
        self.fixed = fixed   # when it's quantifier (most, many), whether it has been fixed
        self.note = note     # note: "at-most", "at-least", "at-most-N", "at-least-N"
    def copy(self):
        cat = copy.deepcopy(self.cat) # recursively create new copy
        return LeafNode(self.depth,cat,self.chunk,self.entity,self.lemma,
                        self.pos,self.span,self.start,self.word)
    # def word_wholeStr(self):
    #     return self.word

    def __str__(self):
        return "lf: {} {} {} {} {} mono:{} imp:{} {}".format(self.cat,self.cat.semCat,self.word,self.pos,
                                              self.depth,self.cat.monotonicity,
                                              self.impSign,self.visited)
    def __repr__(self):
        return self.__str__()

class NonTermNode:
    def __init__(self,depth=None,cat=None,ruleType=None,wholeStr='',impType=None,note=None):
        self.parent = None; self.children = []; self.sisters = []
        self.depth = depth
        self.cat = cat; self.ruleType = ruleType
        self.wholeStr = wholeStr.upper()
        self.visited = False  # whether visited or not when assigning plus/minus sign
        self.span_id = None   # an id, for mytree2transccg.py
        if impType is None: self.impType = ImpType()
        else: self.impType = impType  # type of implicative
        self.impSign = None   # sign of implicative
        self.note = note     # note: "at-most", "at-least", "at-most-N", "at-least-N"
    def copy(self):
        cat = copy.deepcopy(self.cat)  # recursively create new copy
        newNode = NonTermNode(self.depth, cat, self.ruleType, self.wholeStr)
        # recursively build all descendents
        self.copyHelper(newNode)
        return newNode
    def copyHelper(self, newNode):
        # build all descendents
        for child in self.children:
            if len(child.children) == 0:  # LeafNode
                newNode.children.append(child.copy())
            else:  # NonTermNode
                newNode.children.append(child.copy())
    def assignWholeStr(self):
        """ get wholeStr """
        self.wholeStr = self.assignWholeStrHelper(self)
    def assignWholeStrHelper(self, node):
        if len(node.children) == 0: return node.wholeStr
        else:
            return ' '.join([ child.wholeStr for child in node.children ])
    def set_children(self, children):
        """  set up my child/children  """
        self.children = children
        self.assignWholeStr()
        if len(children) == 0: pass
        elif len(children) == 1:
            children[0].parent = self
            children[0].sisters = []
        else:  # 2 children
            children[0].parent, children[1].parent = self, self
            children[0].sisters = [children[1]]
            children[1].sisters = [children[0]]
    def word_wholeStr(self):
        """ return wholeStr by concatenating word, not lemma """
        return self.word_wholeStr_helper(self)
    def word_wholeStr_helper(self, node):
        if len(node.children) == 0: return node.word_raw
        else:
            return ' '.join([ self.word_wholeStr_helper(child) for child in node.children ])
    def __str__(self):
        return "nt: {} {} {} {} {} {}".format(self.cat,self.cat.semCat,
                                              self.ruleType,self.depth,
                                              self.cat.monotonicity,self.visited)
    def __repr__(self):
        return self.__str__()

class SemCat:
    def __init__(self, semCatStr=None, IN=None, OUT=None, marking=None): # '+'):
        # TODO initialize marking as '+' or None?
        ''' if it's just e or t, then it will be assigned to OUT, and IN=None;
        that is, there are only two basic SemCat: e and t
        all the others are built recursively based on these two '''
        self.IN = IN     # (e,t): also a SemCat
        self.OUT = OUT   # t: also a SemCat
        self.marking = marking   # + or -, similar to lex_polarity
        if semCatStr:
            self.semCatStr = semCatStr  # NP has sem cat: ((e,t),t), no - +
        else:
            self.semCatStr = '({},{})'.format(self.IN, self.OUT)
            self.semCatStr = self.semCatStr.replace('-','').replace('+','')
    def assignRecursive(self, plusORminus, exclude):
        ''' assign +/- recursively to every --> inside
        excluding semCat of the type in exclude '''
        self.assignRecursiveHelper(self, plusORminus, exclude)
    def assignRecursiveHelper(self, semcat, plusORminus, exclude):
        if semcat is None: return
        elif semcat.semCatStr in {"(e,t)", "e", "et"}: return
        else:
            if semcat.semCatStr not in exclude:
                semcat.marking = plusORminus
                # print(semcat)
                self.assignRecursiveHelper(semcat.IN, plusORminus, exclude)
                self.assignRecursiveHelper(semcat.OUT, plusORminus, exclude)
    def getsemCatStrWithPM(self):
        """ return semCatStr with + - """
        if (self.IN is None) and (self.OUT is None):
            return '{}'.format(self.semCatStr)
        if self.marking:
            return '({},{}{})'.format(self.IN, self.marking, self.OUT)
        return '({},{})'.format(self.IN, self.OUT)
    def __str__(self):  # has + -
        return self.getsemCatStrWithPM()
    def __repr__(self):
        return self.getsemCatStrWithPM()

class ImpType:
    """ type for implicatives, according to Karttunen 2012, e.g. +-|-+ """
    def __init__(self, lemma=None, pos=None):
        self.impType_str = None  # for most verbs, it is none
        if lemma and pos:
            lemma = lemma.lower()
            if pos.startswith("V"):  # implicatives must be verbs
                # crucial: TODO
                # I add px to mean "no entailment in positive env
                # should ALL other verbs get "px|nx"??? TODO
                if lemma in IMP_pp_nn: self.impType_str = "pp|nn"
                elif lemma in IMP_pp: self.impType_str = "pp"
                elif lemma in IMP_nn: self.impType_str = "nn"
                elif lemma in IMP_pn_np: self.impType_str = "pn|np"
                elif lemma in IMP_pn: self.impType_str = "pn"
                elif lemma in IMP_np: self.impType_str = "np"
                elif lemma in IMP_px_nx: self.impType_str = "px|nx"
                # else:  # all other verbs # test case: want to should entail nothing
                #     self.impType_str = "px|nx"
            # custom words
            elif lemma in {"not", "n't"}:
                self.impType_str = "pn|np"

class Cat:
    '''
    we need to parse a type into
    1) direction, 2) left, 3) right
    e.g.
    buy (S\+NP)/+NP: direction: r, left: S\+NP, right: +NP
    # in case of a simple category, the type will be in both left and right:
    John N: direction: s, left N, right: N
    '''

    def __init__(self, originalType=None, word=None):
        self.direction = None       # str: \=l, /=r and s(single)
        self.left = None            # another Cat object
        self.right = None           # another Cat object
        self.originalType = None    # str: (S\+NP)/+NP, or NP[nb]/N
        self.typeWOpolarity = None  # str: (S\NP)/NP, or NP[nb]/N, i.e. comes w/ feats
        self.typeWOfeats = None     # str: get rid of extra features like [nb]: NP/N
        self.monotonicity = None    # str: [UP, DOWN]
        self.lex_polarity = None    # str: [i, r], c.f. van Eijck's algorithm
        self.word = word            # str: if leafNode, then it has word
        # ------- SEMANTIC CAT ------- #
        self.semCat = SemCat()      # SemCat Object: e,t type
        # ------- END: SEMANTIC CAT ------- #
        self.regexBrk = '\[[^\[\]]+?\]'  # deepcopy cannot handle compiled regex
        if originalType:
            self.originalType = originalType
        else:  # a null Cat
            return
        if ('/' not in self.originalType) and ('\\' not in self.originalType):
            self.processBasicType()
        else:
            self.processComplexType()

        self.typeWOpolarity = self.originalType.replace('_i','').replace('_r','')
        self.typeWOfeats = re.sub(self.regexBrk, '', self.typeWOpolarity)

        # TODO why this? intransitive verb = (((e,t),t),t)
        # if self.semCat.semCatStr == '(((e,t),t),t)':
        #     self.semCat.marking = '+'

    # def copy(self):
    #     cat = copy.deepcopy(self.cat) # recursively create new copy
    #     return LeafNode(self.depth,cat,self.chunk,self.entity,self.lemma,
    #                     self.pos,self.span,self.start,self.word)

    def processBasicType(self):
        ''' basicType: NP, S, N. I.e. with out slashes '''
        self.direction = 's'
        self.left = self.right = None
        self.typeWOpolarity = self.originalType.replace('_i', '').replace('_r', '')
        self.originalType = self.typeWOpolarity
        # ------- SEMANTIC CAT ------- #
        # can only be S, N, NP, pp
        self.typeWOfeats = re.sub(self.regexBrk, '', self.typeWOpolarity)
        if self.typeWOfeats.upper() == 'S': # t
            self.semCat = SemCat(**{'semCatStr':'t'})

        elif self.typeWOfeats.upper() == 'N': # e,t
            # IN = SemCat(**{'OUT':'e','semCatStr':'e'})
            # OUT = SemCat(**{'OUT':'t','semCatStr':'t'})
            E = SemCat(**{'semCatStr':'e'})
            T = SemCat(**{'semCatStr':'t'})
            self.semCat = SemCat(**{'IN':E,'OUT':T})

        elif self.typeWOfeats.upper() == 'NP': # (e,t),t
            E = SemCat(**{'semCatStr':'e'})
            T = SemCat(**{'semCatStr':'t'})
            IN = SemCat(**{'IN':E,'OUT':T})
            OUT = SemCat(**{'semCatStr':'t'})
            self.semCat = SemCat(**{'IN':IN,'OUT':OUT})
            # TODO relative pronoun 'that' should have NP+ in the last NP
            # (NP\NP)/(S/NP+)
            if (self.word is not None) \
                and (self.word.upper() in {'WHO', 'THAT', 'WHICH'}):
                self.semCat = SemCat(**{'IN': IN, 'OUT': OUT, 'marking': '+'})

        elif self.typeWOfeats.upper() in ['.', ',']:  # punctuation
            self.semCat = SemCat()

        elif self.typeWOfeats.upper() == 'PP': # TODO
            self.semCat = SemCat(**{'semCatStr':'pp'})

        elif self.typeWOfeats.upper() == 'CONJ': # TODO
            if self.word.upper() == 'AND': # TODO and is +?
                self.semCat = SemCat(**{'semCatStr':'CONJ','marking':'+'})
            elif self.word.upper() == 'OR':  # TODO +?
                self.semCat = SemCat(**{'semCatStr':'CONJ','marking':'+'})
            elif self.word.upper() == 'BUT':
                self.semCat = SemCat(**{'semCatStr':'CONJ','marking':'+'})
            else:
                raise ErrorCat('unable to create semCat for conjunction {}'.format(self.word))

        elif self.typeWOfeats.upper() == 'PR':  # preposition
            self.semCat = SemCat(**{'semCatStr':'pr'})

        elif self.typeWOfeats.upper() == ':':
            self.semCat = SemCat(**{'semCatStr':':'})

        else:
            self.semCat = SemCat()
            raise ErrorCat('no semCat for basic type: {}\noriginalType: {}'.format(self.typeWOfeats,
                                                                                   self.originalType))
        # ------- END: SEMANTIC CAT ------- #

    def processComplexType(self):
        ''' originalType has either / or \, 
        process originalType into left, right and direction '''

        # need to remove _r, (, ) if originalType == (S_i/VP)_r,
        if self.originalType[-2:] in ['_r', '_i']:
            if self.originalType[-3] != ')':
                self.originalType = self.originalType[:-2]  # A_r --> A
            else:
                self.originalType = self.originalType[1:-3]  # remove ( and )

        # if the left part has no brackets: e.g. XP\((XP/YP)\ZP)
        if not self.originalType.startswith('('):
            ind1 = self.originalType.find('\\')  # ind1 is the index of the left slash
            ind2 = self.originalType.find('/')  # ind2 is the index of the right slash
            ind = ind1  # ind of the first slash, first set to ind1
            self.direction = 'l'

            if ind1 == -1 and ind2 != -1:  # only has /
                self.direction = 'r'  # right
                ind = ind2
            elif ind2 == -1 and ind1 != -1:  # only has \
                self.direction = 'l'  # left
            else:  # has both / and \
                if ind2 < ind1:  # first slash is /
                    ind = ind2
                    self.direction = 'r'

            # now ind is the critical slash that separates left and right
            try:
                if self.originalType[(ind-2):ind] in ['_i', '_r']:
                    self.lex_polarity = self.originalType[(ind-1):ind]
            except IndexError: pass
            self.left = self.originalType[:ind]
            right_tmp = self.originalType[(ind + 1):]

            right_tmp = self.stripOneChar(right_tmp, '(')
            self.right = self.stripOneChar(right_tmp, ')')

        # if the left part has brackets: e.g. ((XP\X)/XP)\(((X\Y)/Z)\A)
        else:
            numLB = 1  # number of left brackets '('
            ind = 1  # the index for / or \

            while numLB > 0:
                if self.originalType[ind] == '(':
                    numLB += 1
                elif self.originalType[ind] == ')':
                    numLB -= 1
                ind += 1

            # assign i or r to lex_polarity and
            # handle cases like: every (TV\VP_i)_r/CN
            # now ind is 9 = the ind after the last ')', which correspond to _
            # we want ind to be 11, which correspond to /
            try:
                if (self.originalType[ind:(ind+2)] == '_i') \
                        or (self.originalType[ind:(ind+2)] == '_r'):
                    self.lex_polarity=self.originalType[(ind+1):(ind+2)] # i or r
                    ind+=2
            except: pass

            if self.originalType[ind] == '\\':
                self.direction = 'l'
            elif self.originalType[ind] == '/':
                self.direction = 'r'
            else:
                eprint('something went wrong when converting types!')
                eprint(self.originalType, self.originalType[ind])
                raise ErrorCat()

            self.left = self.originalType[:ind]
            self.right = self.originalType[(ind + 1):]

            if (not self.left[-2:] == '_r') and (not self.left[-2:] == '_i'):
                self.left = self.stripOneChar(self.left, '(')
                self.left = self.stripOneChar(self.left, ')')
            if (not self.right[-2:] == '_r') and (not self.right[-2:] == '_i'):
                self.right = self.stripOneChar(self.right, '(')
                self.right = self.stripOneChar(self.right, ')')

        self.left = Cat(self.left, self.word)  # recursively build Cat
        self.right = Cat(self.right, self.word)  # recursively build Cat

        # if the word is 'who', then assign '+' to every slash TODO why???
        if (self.word is not None)\
                and (self.word.upper() in {'WHO', 'THAT', 'WHICH'}):
            self.semCat = SemCat(**{'IN': self.right.semCat,
                                    'OUT': self.left.semCat, 'marking':'+'})
        else:
            self.semCat = SemCat(**{'IN': self.right.semCat,
                                    'OUT': self.left.semCat})

    def __str__(self):
        return('{}'.format(self.typeWOpolarity))

    def __repr__(self):
        return('{}'.format(self.typeWOpolarity))

    def stripOneChar(self, stri, char):
        ''' strip the first or last char or both of a string, if it == char:
        e.g. \\this\\ will become \this\ i.e. only strips off one '\' '''
        if len(stri) <= 2:
            return stri
        else:
            if stri[0] == char:
                stri = stri[1:]
            if stri[-1] == char:
                stri = stri[:-1]
            return stri

class ErrorCCGtrees(Exception):
    """ Exception thrown when processing CCGtrees """
    def __init__(self, message=""): Exception.__init__(self, message)
        
class ErrorCCGtree(Exception):
    """ Exception thrown when processing CCGtree """
    def __init__(self, message=""): Exception.__init__(self, message)

class ErrorLeafNode(Exception):
    """ Exception thrown when processing LeafNode """
    def __init__(self, message=""): Exception.__init__(self, message)

class ErrorNonTermNode(Exception):
    """ Exception thrown when processing NonTermNode """
    def __init__(self, message=""): Exception.__init__(self, message)

class ErrorSemCat(Exception):
    """ Exception thrown when processing SemCat """
    def __init__(self, message=""): Exception.__init__(self, message)

class ErrorCat(Exception):
    """ Exception thrown when initializing Cat """
    def __init__(self, message=""): Exception.__init__(self, message)

class ErrorCompareSemCat(Exception):
    """ Exception thrown when CompareSemCat """
    def __init__(self, message=""): Exception.__init__(self, message)

class ErrorAssignEqualMarking(Exception):
    """ Exception thrown when AssignEqualMarking """
    def __init__(self, message=""): Exception.__init__(self, message)

if __name__ == '__main__':
    main()
