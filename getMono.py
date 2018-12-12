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
from IPython.display import Markdown, display

# uparrow: U+2191, down arrow: U+2193

__author__ = "Hai Hu; Larry Moss"
__email__ = "huhai@indiana.edu; lmoss@indiana.edu"

def main():
    # -------------------------------------
    # parse cmd arguments
    description = """
    Polarize CCG trees. Authors: Hai Hu, Larry Moss
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-s', '--sentNo', dest='sentNo', type=str, nargs='+', default=['all'],
                        help='index(s) of sentence to process. E.g. "2", "3 5", "all" ' \
                             "[default: %(default)s]")
    parser.add_argument('-p', dest='parser', default='candc', choices=['candc', 'easyccg'],
                        help='parser of your choice: candc, easyccg ' \
                             "[default: %(default)s]")
    parser.add_argument('-v', dest='verbose', choices=[-1,0,1,2,3], type=int, default=-1,
                        help='verbose: -1: None, 0: after fixTree(), '
                             '1: after mark(), 2: after polarize(), \n3: all ' \
                             "[default: %(default)s]")
    parser.add_argument('-t', dest='test', action='store_const', const=True, default=False,
                        help='if -t, run test()')
    args = parser.parse_args()
    # -------------------------------------

    if args.test:
        print('in test')
        test()
        exit()
    if args.sentNo == ['all']: args.sentNo = []

    # intialize trees
    trees = CCGtrees()

    if args.parser == 'candc':
        trees.readCandCxml('tmp.candc.parsed.xml')
    else: trees.readEasyccgStr('tmp.easyccg.parsed.txt')

    for idx, t in trees.trees.items():
        if args.sentNo:
            if str(idx) not in args.sentNo:
                continue
        print()
        print('-' * 20)
        print('tree {}\n'.format(idx))

        if args.parser == 'candc': t.fixTree()  # only fix the tree if using candc
        if args.parser == 'easyccg': t.fixMost()

        if args.verbose in [0, 3]: t.printTree()

        t.mark()
        if args.verbose in [1, 3]: t.printTree()

        t.polarize()
        if args.verbose in [2, 3]: t.printTree()

        t.printSent()
        # t.printSentLatex()

        # testTrees(trees)

def printmdcolor(string, color=None):
    colorstr = "<span style='color:{}'>{}</span>".format(color, string)
    display(Markdown(colorstr))

def printmd(string):
    mystr = "<span>{}</span>".format(string)
    display(Markdown(mystr))

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
    """ test compareSemCat(): passed """
    left = Cat(originalType=r'(S[dcl]\NP)/NP')
    left.semCat.marking = '+'
    left.semCat.OUT.marking = '+'

    right = Cat(originalType=r'(S[dcl]\NP)/NP')
    right.semCat.IN.marking = '-'

    t = CCGtree()
    t.compareSemCat(right.semCat, left.semCat, 'parent')

    return

    ''' test Cat constructor '''
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

class CCGtrees():
    def __init__(self):
        self.trees = {}
        self.numTrees = 0

    def readCandCxml(self, xml_fn, treeIdx=None):  # treeIdx starts at 0
        print('building trees from candc output', file=sys.stderr)
        soup = BeautifulSoup(open(xml_fn).read(), 'lxml')
        counterSent = -1
        for ccgXml in soup.find_all('ccg'):
            counterSent += 1
            if treeIdx:
                if counterSent != treeIdx:
                    continue
            # make sure there is only one root:
            try:
                assert len(ccgXml.find_all('rule', recursive=False)) == 1
            except AssertionError:
                raise ErrorCCGtrees('more than 1 root')

            #### build the tree  ####
            eprint('building tree {}...'.format(counterSent))
            tree = CCGtree(ccgXml=ccgXml)
            self.trees[counterSent] = tree

        eprint('\ntrees built from candc output!\n\n')

    def readEasyccgStr(self, easyccg_fn, treeIdx=None):  # treeIdx starts at 0
        eprint('building trees from easyccg output')
        easyccg_str = open(easyccg_fn).readlines()

        # for each tree
        counterSent = -1
        for tree_str in easyccg_str:
            if tree_str.startswith('ID='): continue
            counterSent += 1
            # if counterSent == 1: break
            eprint('building tree {}...'.format(counterSent))
            tree = CCGtree(easyccg_tree_str=tree_str)
            self.trees[counterSent] = tree

        eprint('\ntrees built from easyccg output!\n\n')

class CCGtree():
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
        # wholeStr = 'chased some cat' / 'bird'
        self.wholeStr = ''

        # all the inferences we can get by using one replacement in a list
        self.inferences = []  # a list of CCGtrees

        self.numInfTotal = 0  # total num of inferences recursively

        # a list of tuples (y1, y2), storing the two types in a 'tr' rule that should
        # be the same, i.e. the two y's in:
        #        x
        #  ------------tr
        #   (x-->y1)-->y2
        self.trTypes = []

        # build tree based on xml
        if kwargs.get('ccgXml') is not None:
            self.build_CandC(kwargs.get('ccgXml'))
        elif kwargs.get('easyccg_tree_str') is not None:
            # build tree from easyccg output string
            self.build_easyccg(kwargs.get('easyccg_tree_str'))
        elif kwargs.get('NonTermNode') is not None:
            # build tree from NonTermNode
            self.root = kwargs.get('NonTermNode')
            self.buildFromRoot()
            self.regetDepth()
        elif kwargs.get('TermNode') is not None:
            # build tree from LeafNode
            self.root = kwargs.get('TermNode')
            self.buildFromRoot()
            self.regetDepth()
        else:
            pass
            # raise ErrorCCGtree('wrong initialization of CCGtree!')

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
        s = ''
        for lfnode in self.leafNodes:
            s+='{}{} '.format(lfnode.word, lfnode.cat.monotonicity)
        print(s.replace('DOWN', '\u2193').replace('UP', '\u2191').\
              replace('UNK', '='), file=stream)

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

    def printAllInferences(self):
        '''  print all inferences of a ccgtree   '''
        print('\n-- original sentence:\n')
        self.printSent()
        self.printAllInferencesHelper(self, 1)
        print('\n-- {} inferences in total'.format(self.numInfTotal))

    def printAllInferencesHelper(self, ccgtree, level):
        if len(ccgtree.inferences) == 0:
            # print('no inferences!')
            return
        for inf in ccgtree.inferences:
            self.numInfTotal += 1
            print('\n*{}* replacements:'.format(level), end='\n\n')
            # inf.printSentLatex()
            inf.printSent()
            self.printAllInferencesHelper(inf, level+1)

    def fixTree(self):
        ''' fix most and RC problem '''
        self.fixMost()
        self.fixRC()

    def replacement(self, k):
        '''  replacement for inference; k is knowledge  '''
        # newNodes is a list. there might be multiple things to replace in each run.
        # e.g. beagle < [dog, animal]
        newNodes = None

        for ind in range(len(self.allNodes)):
            node = self.allNodes[ind]
            # print('***'+node.wholeStr+'***', end='   ')
            # print('***'+node.cat.monotonicity+'***')
            if node.wholeStr in k.frags.keys():
                # replacement for once only!!
                # get index of node in node.parent.children
                i = node.parent.children.index(node)

                # TODO check if POS/cat is the same??
                # check the monotonicity to see whether can replace
                # make sure cat is the same: e.g. NP = NP
                if (node.cat.monotonicity == 'UP') and \
                        (len(k.frags[node.wholeStr].big) != 0) and \
                        node.cat.typeWOfeats == \
                                k.frags[node.wholeStr].ccgtree.root.cat.typeWOfeats:
                    # replace node with the first thing bigger than it
                    # print('\nfound a node to replace:', node.wholeStr)
                    # print('replace it with        :', k.frags[node.wholeStr].big[0].ccgtree.root.wholeStr)
                    # print('cat must be the same:')
                    # print(node.cat.typeWOfeats)
                    # print(k.frags[node.wholeStr].ccgtree.root.cat.typeWOfeats)
                    newNodes = k.frags[node.wholeStr].big  # a list

                if (node.cat.monotonicity == 'DOWN') and \
                        (len(k.frags[node.wholeStr].small)!=0) and \
                        node.cat.typeWOfeats == \
                                k.frags[node.wholeStr].ccgtree.root.cat.typeWOfeats:
                    # print('cat must be the same:')
                    # print(node.cat.typeWOfeats)
                    # print(k.frags[node.wholeStr].ccgtree.root.cat.typeWOfeats)
                    newNodes = k.frags[node.wholeStr].small  # a list

                if newNodes is not None:
                    for newNode in newNodes:  # newNode is a Fragment
                        newNode = newNode.ccgtree.root

                        # -----------------------------
                        # SET POS and CAT for newNode
                        # !! newNode.pos, newNode.cat came from building the knowledge
                        # could be incomplete
                        try:
                            if newNode.pos is None:
                                newNode.pos = node.pos; newNode.cat = node.cat
                                print(newNode.pos, newNode.cat)
                                print(node.pos, node.cat)
                            elif newNode.pos[0] != node.pos[0]:  # e.g. newNode=V, node=N
                                print('!! mismatch in knowledge pair:', newNode, node)
                                continue
                            elif (newNode.pos == node.pos) and (newNode.cat == newNode.cat):
                                pass
                            else:  # e.g. both are N
                                newNode.pos = node.pos; newNode.cat = node.cat
                        except AttributeError:  # NonTermNode does not have pos
                            # print(newNode.cat, node.cat)
                            pass

                        # --------------------------
                        # NOW build new tree to add to inference
                        # initialize new tree
                        newTree = copy.deepcopy(self)
                        newTree.inferences = []
                        oldNode = newTree.allNodes[ind]  # important: locate the oldNode in newTree

                        # replace oldNode w/ newNode
                        newNode = copy.deepcopy(newNode)  # newNode is from K, need to make a new instance
                        oldNode.parent.children[i] = newNode
                        newNode.parent = oldNode.parent
                        # fix sister node
                        if len(newNode.parent.children) > 1:
                            newNode.parent.children[0].sisters = [newNode.parent.children[1]]
                            newNode.parent.children[1].sisters = [newNode.parent.children[0]]

                        # rebuild tree
                        newTree.buildFromRoot()
                        newTree.regetDepth()
                        newTree.mark()
                        newTree.polarize()

                        # add to inferences
                        self.inferences.append(newTree)

                newNodes = None

        if len(self.inferences) == 0:
            newTree = None  # release mem
            print('Nothing for replacement')

    def replaceRC(self):
        '''
        e.g. some young man [who likes dogs] likes cats
        infer: some man likes cats
        Remove restrictive RC if it has *UP* polarity; then add to
         CCGTree.inferences
        '''
        # detect all nonTermNodes which are RCs with polarity *UP*:
        RCs = []
        for node in self.nonTermNodes:
            if node.cat.typeWOfeats == r'NP\NP' and \
                node.children[0].wholeStr.upper() in ['THAT','WHO','WHOM','WHICH']:
                if node.cat.monotonicity == 'UP':
                    RCs.append(node)

        # remove RC and add to inferences

        # old tree:
        #   N young man      NP\NP who likes dogs => RC
        #  ------------lex
        #    NP  => NP1
        #   ----------------------------- fa
        #                 NP  => NP2
        #             ---------unlex (my rule)
        #  NP/N some      N
        #  ------------------
        #        NP

        # now we want to move NP1 to NP2
        #            N young man
        #           ------------lex
        #                NP
        #             ---------unlex (my rule)
        #  NP/N some      N
        #  ------------------
        #        NP

        for RC in RCs:
            # initialize new tree
            newTree = copy.deepcopy(self)  # TODO
            newTree.inferences = []

            # get index of RC in nonTermNodes
            ind = self.nonTermNodes.index(RC)
            RC  = newTree.nonTermNodes[ind]  # RC should be in newTree

            # get NP1 and NP2
            node_NP1 = RC.sisters[0]
            node_NP2 = RC.parent

            # adjust pointer
            # indNP2 is the index of NP2 in NP2.parent.children
            indNP2 = node_NP2.parent.children.index(node_NP2)
            node_NP2.parent.children[indNP2] = node_NP1
            node_NP1.parent = node_NP2.parent

            # rebuild the tree; this takes care of:
            # self.nonTermNodes, self.leafNodes and self.allNodes
            newTree.buildFromRoot()
            newTree.regetDepth()
            newTree.mark()
            newTree.polarize()

            # sanity check
            # newTree.printSent()
            # newTree.printTree()
            # print(len(newTree.leafNodes))
            # print(len(newTree.nonTermNodes))
            # print(len(newTree.allNodes))

            self.inferences.append(newTree)

    def getAllDescendants(self, nonTermNode):
        '''
        Returns a list of all descendants of a nonTermNode (including itself)
        '''
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
                    eprint('equate marking:', node)
                    self.equate_marking(node.cat.semCat.IN, node.cat.semCat.OUT)
                    eprint('after equate marking:', node)

    def mark_LeafNodes(self):
        ''' mark leaf nodes '''
        for token in self.leafNodes:
            # -----------------------
            # quantifiers
            if token.word.upper() in ['SOME', 'A', 'AN']:  # + +
                # if token.cat.semCat.semCatStr == '((e,t),((e,t),t))':
                token.cat.semCat.marking = '+'
                token.cat.semCat.OUT.marking = '+'
            elif token.word.upper() in ['EVERY', 'ALL']:  # - +
                # if token.cat.semCat.semCatStr == '((e,t),((e,t),t))':
                token.cat.semCat.marking = '-'
                token.cat.semCat.OUT.marking = '+'
            elif token.word.upper() == 'NO':  # - -
                # if token.cat.semCat.semCatStr == '((e,t),((e,t),t))':
                token.cat.semCat.marking = '-'
                token.cat.semCat.OUT.marking = '-'
            # TODO other DTs: a, the, this, that?

            # -----------------------
            # TODO negation
            elif token.word.upper() in ['NOT', "N'T"]:  # N'T: (S\NP)\(S\NP)
                token.cat.semCat.marking = '-'  # check semCatStr??
                # TODO is this correct?
                token.cat.semCat.OUT.marking = '+'
                token.cat.semCat.IN.marking = '+'
                # token.cat.semCat.OUT.IN.marking = '+'  # (S+\NP+)-\(S+\NP)
                # token.cat.semCat.IN.IN.marking = '+'  # (S+\NP)-\(S+\NP+)

            # -----------------------
            # TODO nouns
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
                    token.cat.semCat.IN.marking = '+'
                    token.cat.semCat.IN.IN.marking = '+'
                    token.cat.semCat.OUT.IN.marking = '+'  # (S+\NP+)-/(S+\NP+)

                else:
                    token.cat.semCat.marking = '+'
                    if token.cat.typeWOfeats == r'(S\NP)/NP':  # transitive verb
                        token.cat.semCat.OUT.marking = '+'  # make it (S+\NP)+/NP
                    if token.cat.typeWOfeats == r'((S\NP)/PP)/NP':  # 'put' with a PP argument
                        token.cat.semCat.OUT.marking = '+'  # make it ((S\NP)/+PP)+/NP
                    # if (token.word.upper() in ['DID', 'DO']) and \
                    #         (token.cat.typeWOfeats == r'(S\NP)/(S\NP)'):  # 'did' in 'did not'
                    if token.cat.typeWOfeats == r'(S\NP)/(S\NP)':
                        # 'did' in 'did not', 'want' in I want to go
                        token.cat.semCat.OUT.marking = '+'
                        token.cat.semCat.IN.marking = '+'  # (S+\NP)+/(S+\NP)
                        # token.cat.semCat.IN.IN.marking = '+'   # (S+\NP)+/(S+\NP+)
                        # token.cat.semCat.OUT.IN.marking = '+'  # (S+\NP+)+/(S+\NP)
                    if token.cat.typeWOfeats == r'(S\NP)/PP':  # 'ask' as in 'ask about'
                        token.cat.semCat.OUT.marking = '+'

            # TODO model verbs
            elif token.pos.upper() == 'MD':
                # can: (S\NP)/(S\NP)
                token.cat.semCat.marking = '+'
                token.cat.semCat.IN.marking = '+'  # ??
                token.cat.semCat.OUT.marking = '+'  # ??

            # TODO to
            elif (token.pos.upper() == 'TO') and \
                    (token.cat.typeWOfeats == r'(S\NP)/(S\NP)'):
                # 'to' in 'I want to', 'refused to' # (S+\NP)+/(S+\NP)
                token.cat.semCat.marking = '+'
                token.cat.semCat.OUT.marking = '+'
                token.cat.semCat.IN.marking = '+'
                # token.cat.semCat.OUT.IN.marking = '+'
                # token.cat.semCat.IN.IN.marking = '+'  # (S+\NP+)+/(S+\NP+)

            # TODO adverbs 1
            elif (token.pos.upper() == 'RB') and \
                    (token.cat.typeWOfeats in [r'(S\NP)/(S\NP)',
                                               r'(S\NP)\(S\NP)']) and \
                    (token.word.upper() not in ['NOT', "N'T"]):
                # adverbs; make it (S+\NP)+/(S+\NP)
                token.cat.semCat.marking = '+'
                token.cat.semCat.OUT.marking = token.cat.semCat.IN.marking = '+'

            # TODO adverbs 2 r'S\NP'
            elif (token.pos.upper() == 'RB') and \
                    (token.cat.typeWOfeats in [r'S\NP']) and \
                    (token.word.upper() not in ['NOT', "N'T"]):
                # adverbs; make it S+\NP
                token.cat.semCat.marking = '+'

            # -----------------------
            # TODO adjectives, add +
            elif (token.pos.upper() == 'JJ') and \
                    (token.word.upper() not in ['FAKE']):
                token.cat.semCat.marking = '+'

            # noun as noun modifiers, add +
            elif (token.pos.upper() in ['NN', 'NNP']) and \
                    (token.cat.typeWOfeats == r'N/N'):
                token.cat.semCat.marking = '+'

            # TODO prepositions
            elif token.word.upper() in {'IN', 'ON', 'TO', 'FROM', 'FOR',
                                        'WITHIN'}:
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
            elif token.word.upper() in ['OUTSIDE', 'WITHOUT', 'OUT']:
                if token.cat.typeWOfeats == r'((S\NP)\(S\NP))/NP':  # without
                    token.cat.semCat.marking = '-'
                    token.cat.semCat.OUT.marking = '+'
                    token.cat.semCat.OUT.IN.marking = '+'
                    token.cat.semCat.OUT.OUT.marking = '+'
                    # token.cat.semCat.OUT.IN.IN.marking = '+'
                    # token.cat.semCat.OUT.OUT.IN.marking = '+'  # ((S+\NP+)+\(S+\NP+))-/NP

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
            self.mark_NTN_myparent(node)
            if node.parent.ruleType == 'conj': self.mark_NTN_myparent_conj(node)

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
            if node.parent.ruleType == 'conj': self.mark_NTN_myparent_conj(node)

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
                node.parent.cat.semCat.IN.IN = node.cat.semCat  # TODO
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
                assert parent.cat.semCat.semCatStr == left.cat.semCat.OUT.semCatStr
                assert left.cat.semCat.IN.semCatStr == right.cat.semCat.semCatStr
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
                    assert parent.cat.semCat.IN.semCatStr == left.cat.semCat.IN.semCatStr
                    assert parent.cat.semCat.OUT.semCatStr == right.cat.semCat.OUT.semCatStr
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

        parent = node.parent
        conj = parent.children[0]
        X2 = parent.children[1]
        X1 = parent.sisters[0]
        grandparent = parent.parent

        # first get the cat for conj, and marking on the SLASHES,
        # not on the NP
        # i.e. if right = X, sister = X, then we want conj to be: (X\X)/X
        if conj.cat.typeWOfeats.upper() == 'CONJ':
            X2Type = X2.cat.typeWOpolarity

            # if X2Type X is basic: NP, then conj: (NP\NP)/NP
            # but when X2Type is complex: (S\NP)/NP
            # we need an extra pair of brackets for rightType X:
            # i.e. ((X)\(X))/(X) = (((S\NP)/NP)\((S\NP)/NP))/((S\NP)/NP)
            if '(' in X2Type:
                X2Type = '(' + X2Type + ')'

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
            if (X2.cat.semCat.marking is None) or (X1.cat.semCat.marking is None):
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

        # eprint('---\nafter:\nsemCat1:', semCat1, semCat1.semCatStr)
        # eprint('semCat2:', semCat2, semCat2.semCatStr)

    def compareSemCatHelper(self, semCat1, semCat2, parent):
        """ recursive helper function
        e.g. semCat1 = ((et,-t),((et,t),t))   semCat2 = ((et,t),+((et,t),+t))
        """
        try:
            assert self.semCatGreater(semCat1, semCat2)  # semCat2 is more specific
            semCat1.marking = semCat2.marking
        except AssertionError:
            eprint(semCat1, semCat2)
            eprint(semCat1.marking, semCat2.marking)
            eprint("parent: {}".format(parent))
            raise ErrorCompareSemCat("{} not greater than {}".format(semCat1, semCat2))

        if semCat1.IN:  # if semCat1.IN is not None
            self.compareSemCatHelper(semCat2.IN, semCat1.IN, parent)
        if semCat1.OUT:
            self.compareSemCatHelper(semCat1.OUT, semCat2.OUT, parent)

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
        if NP.marking == '-':  # NP-, flip
            self.polarizeHelper(functor, self.flip(monoDirection))
        elif NP.marking is None:  # NP=
            self.polarizeHelper(functor, 'UNK')
        else:  # NP+
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
                        self.polarizeHelper(right, monoDirection)
                        self.polarizeHelper(left, self.calcMono(right, monoDirection))
                except AttributeError:  # 'LeafNode' (right) object has no attribute 'ruleType'
                    self.polarizeHelper(right, monoDirection)
                    self.polarizeHelper(left, self.calcMono(right, monoDirection))

            elif node.ruleType == 'fa':  # X/Y Y --> X   functor = left
                try:
                    if left.ruleType.upper() == 'CONJ':
                        self.polarizeHelper(right, self.calcMono(left, monoDirection))
                        self.polarizeHelper(left, monoDirection)
                    else:
                        self.polarizeHelper(left, monoDirection)
                        self.polarizeHelper(right, self.calcMono(left, monoDirection))
                except AttributeError:  # 'LeafNode' (left) object has no attribute 'ruleType'
                    self.polarizeHelper(left, monoDirection)
                    self.polarizeHelper(right, self.calcMono(left, monoDirection))

            elif node.ruleType == 'bx':
                # Z/Y Y\X -> Z\X    functor = left
                if node.cat.direction == 'l':
                    self.polarizeHelper(right, monoDirection)
                    self.polarizeHelper(left, self.calcMono(right, monoDirection))

                # Y/X Z\Y -> Z/X    functor = right   # "did not" is this pattern
                else:
                    self.polarizeHelper(left, monoDirection)
                    self.polarizeHelper(right, self.calcMono(left, monoDirection))

            elif node.ruleType == 'fc':  # Z/Y Y/X -> Z/X or Y\X Z\Y -> Z\X
                # Z/Y Y/X -> Z/X    functor = left   ** Object Relative Clause **
                if node.cat.direction == 'r':
                    self.polarizeHelper(right, monoDirection)
                    self.polarizeHelper(left, self.calcMono(right, monoDirection))
                # Y\X Z\Y -> Z\X   functor = right
                else:
                    self.polarizeHelper(left, monoDirection)
                    self.polarizeHelper(right, self.calcMono(left, monoDirection))

            elif node.ruleType == 'conj':  # conjunction
                try:  #
                    if left.pos.upper() == 'CC':
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

    def build_easyccg(self, easyccg_tree_str):
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
                lf_node = LeafNode(depth=0,cat=cat,chunk=chunk,entity=NER,
                                   lemma=lemma,pos=pos,span=1,start=numLeafNode-1,word=token)
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
                # print(ntn_node)
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
        # allNodes
        self.allNodes = self.leafNodes + self.nonTermNodes

    def build_CandC(self, ccgXml):
        ''' build the tree recursively from xml output of CandC '''
        self.root = NonTermNode(depth=-1)  # dummy root; important for building the tree from candc
        self.build_CandC_helper(ccgXml, self.root, -1)
        self.getWholeStrAllNodes()
        # allNodes
        self.allNodes = self.leafNodes + self.nonTermNodes
        # self.printTree()

    def build_CandC_helper(self, nodeXml, Node, depth):
        for childXml in nodeXml.find_all(re.compile('(lf|rule)'), recursive=False):
            if childXml.find('lf') is None: # if the child is leaf
                cat = Cat(**{'originalType':childXml['cat'], 'word':childXml['word']})
                leafNode = LeafNode(depth+1, cat, childXml['chunk'], childXml['entity'],
                                    childXml['lemma'], childXml['pos'], childXml['span'],
                                    childXml['start'], childXml['word'])
                Node.children.append(leafNode)
                leafNode.parent = Node
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

    def fixMost(self):
        if 'MOST' not in self.words:
            return
        # -----------------------------
        # fix trees involving 'most'
        # -----------------------------

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
        nodeMost = None
        nodeMostID = None
        for i in range(len(self.leafNodes)):
            if i == 0:
                if self.leafNodes[i].word.upper() == 'MOST':
                    nodeMost = self.leafNodes[i]
                    nodeMostID = 0
            else: # make sure the word before it is not 'AT'
                if (self.leafNodes[i].word.upper() == 'MOST') and \
                        (self.leafNodes[i-1].word.upper()!='AT'):
                    nodeMost = self.leafNodes[i]
                    nodeMostID = i

        if nodeMost:
            nodeN = nodeMost.parent
            nodeNP = nodeN.parent
            nodeMostSister = nodeMost.sisters[0]

            # get new nodeMost
            nodeMostNew = LeafNode(depth=nodeMost.depth - 1, cat=Cat('NP/N', 'most'),
                                   chunk=nodeMost.chunk, entity=nodeMost.entity,
                                   lemma=nodeMost.lemma, pos=nodeMost.pos,
                                   span=nodeMost.span, start=nodeMost.start,
                                   word=nodeMost.word)
            nodeMostNew.cat.semCat.OUT.marking = '+'
            nodeMostNew.cat.semCat.marking = None
            nodeMostNew.sisters = [nodeMostSister]
            nodeMostNew.parent = nodeNP

            # fix nodeMostSister, and its depth
            nodeMostSister.parent = nodeNP
            self.decreaseDepth(nodeMostSister)

            # fix nodeNP
            nodeNP.ruleType = 'fa'
            nodeNP.children = [nodeMostNew, nodeMostSister]

            # fix self.leafNodes
            self.leafNodes[nodeMostID] = nodeMostNew

        else: # nodeMost = None, i.e. it's "AT MOST"
            return

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
                        'NO', 'SOME', 'EVERY', 'MOST', 'ANY']:
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
                            print('error removing node from nonTermNodes')
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

class LeafNode():
    def __init__(self,depth,cat,chunk,entity,lemma,pos,span,start,word):
        self.parent = None; self.children = []; self.sisters = []
        self.depth = depth

        self.cat = cat; self.chunk = chunk; self.entity = entity
        self.lemma = lemma; self.pos = pos; self.span = span
        self.start = start; self.word = word
        self.wholeStr = word.upper()
        self.visited = True  # whether visited or not when assigning plus/minus sign
        self.span_id = None  # an id, for mytree2transccg.py
    def copy(self):
        cat = copy.deepcopy(self.cat) # recursively create new copy
        return LeafNode(self.depth,cat,self.chunk,self.entity,self.lemma,
                        self.pos,self.span,self.start,self.word)
    def __str__(self):
        return "lf: {} {} {} {} {} {} {}".format(self.cat,self.cat.semCat,self.word,self.pos,
                                              self.depth,self.cat.monotonicity,self.visited)
    def __repr__(self):
        return self.__str__()

class NonTermNode():
    def __init__(self,depth=None,cat=None,ruleType=None,wholeStr=''):
        self.parent = None; self.children = []; self.sisters = []
        self.depth = depth
        self.cat = cat; self.ruleType = ruleType
        self.wholeStr = wholeStr
        self.visited = False  # whether visited or not when assigning plus/minus sign
        self.span_id = None  # an id, for mytree2transccg.py
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
    def __str__(self):
        return "nt: {} {} {} {} {} {}".format(self.cat,self.cat.semCat,
                                              self.ruleType,self.depth,
                                              self.cat.monotonicity,self.visited)
    def __repr__(self):
        return self.__str__()

class SemCat():
    def __init__(self, semCatStr=None, IN=None, OUT=None, marking=None): # '+'):
        # TODO initialize marking as '+' or None?
        ''' if it's just e or t, then it will be assigned to OUT, and IN=None;
        that is, there are only two basic SemCat: e and t
        all the others are built recursively based on these two '''
        self.IN = IN # (e,t): also a SemCat
        self.OUT = OUT # t: also a SemCat
        self.marking = marking # + or -, similar to lex_polarity
        if semCatStr:
            self.semCatStr = semCatStr  # NP has sem cat: ((e,t),t), no - +
        else:
            self.semCatStr = '({},{})'.format(self.IN, self.OUT)
            self.semCatStr = self.semCatStr.replace('-','').replace('+','')
    def assignRecursive(self, plusORminus):
        ''' assign +/- recursively to every --> inside '''
        self.assignRecursiveHelper(self, plusORminus)
    def assignRecursiveHelper(self, semcat, plusORminus):
        if semcat is None: return
        else:
            # print(semcat)
            semcat.marking = plusORminus
            self.assignRecursiveHelper(semcat.IN, plusORminus)
            self.assignRecursiveHelper(semcat.OUT, plusORminus)
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

class Cat():
    '''
    we need to parse a type into
    1) direction, 2) left, 3) right
    e.g.
    buy (S\+NP)/+NP: direction: r, left: S\+NP, right: +NP
    # in case of a simple category, the type will be in both left and right:
    John N: direction: s, left N, right: N
    '''

    def __init__(self, originalType=None, word=None):  # , word, direction, left, right
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
            # E = SemCat(**{'OUT':'e','semCatStr':'e'})
            # T = SemCat(**{'OUT':'t','semCatStr':'t'})
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
