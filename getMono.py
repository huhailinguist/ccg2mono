#!/usr/bin/env python3
'''
parse candc xml and get monotonicity

PIPELINE:
1. read in C&C output.xml, parse the trees into out data structure

For each tree:
2. getPM: assign plus and minus signs to each node
2.1. getPM for leafNodes
2.2. getPM for nonTermNodes

3. polarize

4. fit output to xml/html format

Hai Hu, Feb, 2018
'''

import sys, os, re, copy
from sys import exit
from bs4 import BeautifulSoup
from IPython.display import Markdown, display

# uparrow: U+2191, down arrow: U+2193

helpM = '''
Usage: python3 getMono.py (sentNo.) (v1/v2/v3/vall)

- sentNo.: index of sent you want to check, starting from 0,
           if not provided, all sents will be printed

- v1/v2/v3/vall:
  - v1: print tree before getPM()
  - v2: print tree before polarize()
  - v3: print tree after polarize()
  - vall: v1+v2+v3

'''

def main():
    if '-h' in sys.argv:
        print(helpM)
        exit(0)
    sentToTest = None
    if len(sys.argv) >= 2:
        sentToTest = int(sys.argv[1])  # sentence to test
        print('sentToTest:', sentToTest)
    trees = CCGtrees()
    trees.readCandCxml('tmp.candc.xml')

    for idx, t in trees.trees.items():
        if sentToTest is not None:
            if idx != sentToTest:
                continue
        print()
        print('-' * 20)
        print('tree {}\n'.format(idx))
        if any(x in sys.argv for x in ['-v1', '-vall']):
            t.printTree()

        t.fixTree()

        t.getPM()
        if any(x in sys.argv for x in ['-v2', '-vall']):
            t.printTree()

        t.polarize()
        if any(x in sys.argv for x in ['-v3', '-vall']):
            t.printTree()

        t.printSent()
        # t.printSentLatex()

        # test(trees)

def printmdcolor(string, color=None):
    colorstr = "<span style='color:{}'>{}</span>".format(color, string)
    display(Markdown(colorstr))

def printmd(string):
    mystr = "<span>{}</span>".format(string)
    display(Markdown(mystr))

def test(trees):
    '''  test other constructors of CCGtree: passed  '''
    t = trees.trees[3]
    node = t.root.children[0].children[0]
    print(node)

    newtree = CCGtree(NonTermNode=node)
    newtree.printTree()
    print(newtree.words)
    print(newtree.wholeStr)

class CCGtrees():
    def __init__(self):
        self.trees = {}
        self.numTrees = 0

    def readCandCxml(self, xml_fn, treeIdx=None):  # treeIdx starts at 0
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
                print('more than 1 root')
                exit(1)

            #### build the tree  ####
            print('building tree {}...'.format(counterSent))
            tree = CCGtree(ccgXml=ccgXml)
            self.trees[counterSent] = tree

        print('\ntrees built!\n\n')

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
    # def __init__(self, ccgXml=None):
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

        # build tree based on xml
        if kwargs.get('ccgXml') is not None:
            self.build(kwargs.get('ccgXml'))
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
            print('wrong initialization of CCGtree!')
            exit(1)

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

    def printSent(self):
        s = ''
        for lfnode in self.leafNodes:
            s+='{}{} '.format(lfnode.word, lfnode.cat.monotonicity)
        print(s.replace('DOWN', '\u2193').replace('UP', '\u2191').replace('UNK', '='))

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

    def printTree(self):
        self.printTreeHelper(self.root)

    def printTreeHelper(self, node):
        if len(node.children) == 0: # leaf
            print("{}{}\n".format(node.depth * '   ', node))
        else:
            print("{}{}\n".format(node.depth * '   ', node))
            for child in node.children:
                self.printTreeHelper(child)

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
                                # print(newNode.pos, newNode.cat)
                                # print(node.pos, node.cat)
                                # print()
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
                        newTree.getPM()
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
            newTree = copy.deepcopy(self)
            newTree.inferences = []

            # get index of RC in nonTermNodes
            ind = self.nonTermNodes.index(RC)
            RC  = newTree.nonTermNodes[ind]  # RC should be in newTree

            # get NP1 and NP2
            node_NP1 = RC.sisters[0]
            node_NP2 = RC.parent
            # # remove NP1, NP2 from nonTermNodes
            # newTree.nonTermNodes.remove(node_NP1)
            # newTree.nonTermNodes.remove(node_NP2)
            # # remove all descendants of RC
            # des = newTree.getAllDescendants(RC)  # including RC
            # for node in des:
            #     if len(node.children) == 0:  # leafNode
            #         newTree.leafNodes.remove(node)
            #     else:  # nonTermNode
            #         newTree.nonTermNodes.remove(node)

            # adjust pointer
            # indNP2 is the index of NP2 in NP2.parent.children
            indNP2 = node_NP2.parent.children.index(node_NP2)
            node_NP2.parent.children[indNP2] = node_NP1
            node_NP1.parent = node_NP2.parent

            # rebuild the tree; this takes care of:
            # self.nonTermNodes, self.leafNodes and self.allNodes
            newTree.buildFromRoot()
            newTree.regetDepth()
            newTree.getPM()
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

    def getPM(self):
        ''' add plus minus to all nodes '''
        self.getPM_LeafNodes()
        self.getPM_NTN()

    def getPM_LeafNodes(self):
        ''' add plus minus to leaf nodes '''
        # first do leafNodes, i.e. words
        for token in self.leafNodes:
            # quantifiers
            if token.word.upper() in ['SOME', 'A', 'AN']:  # + +
                # if token.cat.semCat.semCatStr == '((e,t),((e,t),t))':
                token.cat.semCat.pm = '+'
                token.cat.semCat.OUT.pm = '+'
            elif token.word.upper() in ['EVERY', 'ALL']:  # - +
                # if token.cat.semCat.semCatStr == '((e,t),((e,t),t))':
                token.cat.semCat.pm = '-'
                token.cat.semCat.OUT.pm = '+'
            elif token.word.upper() == 'NO':  # - -
                # if token.cat.semCat.semCatStr == '((e,t),((e,t),t))':
                token.cat.semCat.pm = '-'
                token.cat.semCat.OUT.pm = '-'

            # negation
            elif token.word.upper() in ["NOT", "N'T"]:  # -
                token.cat.semCat.pm = '-'  # check semCatStr??

            # adjectives, add +
            elif token.pos.upper() == 'JJ':
                token.cat.semCat.pm = '+'

            # # intransitive verbs, add type raising
            # elif token.cat.semCat.semCatStr == '(((e,t),t),t)':
            #     # this is intransitive verb
            #     print('intransitive verb!')
            #     # we consider it to be covertly raised from (e,t), we manually add to it
            #     # a child of type (e,t) TODO: check if (((e,t),t),t) appears in NT node
            #
            #     # create 2 new nodes
            #     newLeafNode = token.copy() # should return a new object, not a pointer
            #     newLeafNode.depth += 1
            #     # fixing cat, semCat for newLeafNode,
            #     E = SemCat(**{'semCatStr': 'e'})
            #     T = SemCat(**{'semCatStr': 't'})
            #
            #     newLeafNode.cat.semCat = SemCat(IN=E,OUT=T)
            #     newNTNode = NonTermNode(token.depth,token.cat,ruleType='tr') # tr=type raising
            #
            #     # fix tree.leafNodes, and tree.nonTermNodes
            #     self.leafNodes[self.leafNodes.index(token)] = newLeafNode
            #     self.nonTermNodes.append(newNTNode)
            #
            #     # fix parent, children pointers
            #     tokenParent = token.parent
            #     idxOldToken = tokenParent.children.index(token)
            #
            #     tokenParent.children[idxOldToken] = newNTNode
            #     newNTNode.parent = tokenParent
            #     newLeafNode.parent = newNTNode
            #
            #     assert len(newNTNode.children)==0
            #     newNTNode.children.append(newLeafNode)
            #
            #     # fix sisters pointers
            #     if token.sisters:
            #         token.sisters[0].sisters[0] = newNTNode
            #         assert len(newNTNode.sisters) == 0
            #         newNTNode.sisters.append( token.sisters[0] )

            # TODO how about other DTs: a, the, this, that?

            # if = ((t,+t),-t)
            elif token.word.upper() == 'IF':
                token.cat.semCat.pm = '-'
                token.cat.semCat.OUT.pm = '+'

            elif token.word.upper() == 'THEN':
                token.cat.semCat.pm = '+'

            elif token.word.upper() == 'IT':
                token.cat.semCat.pm = '+'

            # most N/N: most dogs, then N (most dogs) has a lex rule --> NP
            # at most: (S/S)/(S[asup=true]\NP) S[asup=true]\NP
            elif token.word.upper() == 'MOST':
                # already handled in fixTree
                pass

            # that, who; (token.pos == 'WDT') necessary?
            elif token.word.upper() in ['THAT', 'WHO'] and \
                    (token.pos in ['WDT', 'IN', 'WP']):
                # !! already handled in Cat() !! #
                pass

            # verb, then should be + TODO do we really need it?
            elif token.pos.upper().startswith('VB'):
                token.cat.semCat.pm = '+'
                if token.cat.typeWOfeats == r'(S\NP)/NP':  # transitive verb
                    token.cat.semCat.OUT.pm = '+'  # make it (S+\NP)/NP

            # if the leafNode is NP, e.g. pronouns such as I, make it NP+
            elif token.cat.originalType == 'NP':
                token.cat.semCat.pm = '+'

    def getPM_NTN2(self):
        # another way of getting pm for non terminal nodes
        # we go from every leaf to root, for every node n along the path:
        # we determine +/- for its children, sister, parent.
        # note that any relatives can get +/- from another one.
        # e.g. parent can get it from children; children can also get it from parent
        for node in self.leafNodes:
            self.getPM_NTN2Helper(node)

    def getPM_NTN2Helper(self, node):
        # set pm for sister
        # set pm for children
        # set pm for parent
        # finally do the same for parent, until reaches root
        if node.parent is not None:
            self.getPM_NTN2Helper(node.parent)
        else:  # already at root
            return

    def getPM_NTN(self):
        ''' add plus minus non terminal node '''
        self.getPM_NTNHelper(self.root)
        # get pm for conj
        self.getPM_NTNHelperCONJ(self.root)

    def getPM_NTNHelper(self, node):
        # if leaf node, set up semCat of parent
        if len(node.children) == 0:
            self.getPM_NTNmyparent(node)
        # if it's not terminal node
        else:
            if len(node.children) == 2:  # 2 children
                self.getPM_NTNHelper(node.children[0])  # left child
                self.getPM_NTNHelper(node.children[1])  # right child
                # now fix node.parent
                self.getPM_NTNmyparent(node)
            elif len(node.children) == 1:  # only one child, rule is either 'lex' or 'tr'
                self.getPM_NTNHelper(node.children[0])
                # now fix node itself
                self.getPM_NTNmyparent(node)
            else:
                print('number of children more than 2: {}'.format(node))
                exit(1)

    def getPM_NTNHelperCONJ(self, node):
        ''' get pm for CONJ rule '''
        if len(node.children) == 0:
            if node.parent.ruleType == 'conj':
                self.getPM_NTNmyparentCONJ(node)
        else:
            if len(node.children) == 2:  # 2 children
                self.getPM_NTNHelperCONJ(node.children[0])  # left child
                self.getPM_NTNHelperCONJ(node.children[1])  # right child
                # now fix node.parent
                if node.parent.ruleType == 'conj':
                    self.getPM_NTNmyparentCONJ(node)
            elif len(node.children) == 1:  # only one child, rule is either 'lex' or 'tr'
                self.getPM_NTNHelperCONJ(node.children[0])
                # now fix node itself
                if node.parent.ruleType == 'conj':
                    self.getPM_NTNmyparentCONJ(node)
            else:
                print('number of children more than 2: {}'.format(node))
                exit(1)

    def getPM_NTNmyparentCONJ(self, node):
        parent = node.parent
        left = parent.children[0]
        right = parent.children[1]
        sister = parent.sisters[0]
        #        conj(left)      NP(right)
        #        -------------------------- conj
        # NP(sister)           NP\NP(parent)
        # ----------------------------------- fa/ba
        #             NP(grandparent)

        # if conj is left, then make conj (X\X)/X
        try:
            if left.pos.upper() == 'CC':
                # !! assign parent.OUT pm !! #
                if (right.cat.semCat.pm is None) or (sister.cat.semCat.pm is None):
                    parent.cat.semCat.OUT.pm = None  # this will be grandparent NP
                # if right.pm == parent.sister.pm != None, then parent.parent = that pm
                elif right.cat.semCat.pm == sister.cat.semCat.pm:
                    parent.cat.semCat.OUT.pm = right.cat.semCat.pm
                else:
                    parent.cat.semCat.OUT.pm = None

            else:  # right is conj; this should in theory never happen
                # !! assign parent.OUT pm !! #
                if (left.cat.semCat.pm is None) or (sister.cat.semCat.pm is None):
                    parent.cat.semCat.OUT.pm = None  # this will be grandparent NP
                # if left.pm == parent.sister.pm != None, then parent.parent = that pm
                elif left.cat.semCat.pm == sister.cat.semCat.pm:
                    parent.cat.semCat.OUT.pm = left.cat.semCat.pm
                else:
                    parent.cat.semCat.OUT.pm = None

        except AttributeError:  # also right is conj
            # !! assign parent.OUT pm !! #
            if (left.cat.semCat.pm is None) or (sister.cat.semCat.pm is None):
                parent.cat.semCat.OUT.pm = None  # this will be GRAND PARENT
            # if left.pm == parent.sister.pm != None, then parent.parent = that pm
            elif left.cat.semCat.pm == sister.cat.semCat.pm:
                parent.cat.semCat.OUT.pm = left.cat.semCat.pm
            else:
                parent.cat.semCat.OUT.pm = None

                # if conj is 'and', 'or', then get + ??
                # if conj is 'but', should be (X\X)-/X ??
                # but what about the first slash??? TODO

    def getPM_NTNmyparent(self, node):
        ''' get the minusPlus of node.parent '''
        # if I'm single child, then rule is either 'lex' or 'tr'
        if len(node.sisters) == 0:
            if node.parent.ruleType == 'tr':
                assert node.cat.semCat != node.parent.cat.semCat
                node.parent.cat.semCat.pm = '+'
            elif node.parent.ruleType == 'lex':
                # probably we don't have to do anything
                # 'lex' happens for 'John' or 'reading' in 'this is the book that
                #   I burnt without reading'
                # we want 'John' to be NP+
                node.parent.cat.semCat.pm = '+'
            elif node.parent.ruleType == 'unlex':
                # NP -> N: rule added by myself, for RC, do nothing
                # print('*** unlex rule ***')
                pass
            else:  # terminal node
                pass


        # if I got one sister
        elif len(node.sisters) == 1:
            parent = node.parent
            left = parent.children[0]
            right = parent.children[1]
            if parent.ruleType == 'fa':
                # X/Y Y -> X
                # make sure input and output of FA is correct
                assert parent.cat.semCat.semCatStr == left.cat.semCat.OUT.semCatStr
                assert left.cat.semCat.IN.semCatStr == right.cat.semCat.semCatStr
                parent.cat.semCat = left.cat.semCat.OUT  # ASSIGN PM

                self.compareSemCat(left.cat.semCat.IN, right.cat.semCat, parent)  # IMPORTANT: comparator
                left.cat.semCat.IN = right.cat.semCat

            elif parent.ruleType == 'ba':
                # Y X\Y -> X
                # make sure input and output of BA is correct
                assert parent.cat.semCat.semCatStr == right.cat.semCat.OUT.semCatStr
                try:
                    assert right.cat.semCat.IN.semCatStr == left.cat.semCat.semCatStr
                except AssertionError:
                    print(right)
                    print(left)
                    self.printTree()

                # --- FOR RELATIVE CLAUSES --- #
                # TODO: COULD BE DELETED since fixTree() fixes the RC
                # if X\Y is NP\NP, the RC in English (English RC comes after the head NP)
                # TODO, ONLY do this for RC, but NOT conjunction!
                if (right.cat.typeWOfeats == r'NP\NP') and \
                        (right.ruleType.upper() != 'CONJ'):
                    # then the OUT NP should have the same pm as the IN NP in right
                    # assert right.cat.semCat.OUT.pm is None
                    right.cat.semCat.OUT.pm = left.cat.semCat.pm
                # --- END: FOR RELATIVE CLAUSES --- #

                parent.cat.semCat = right.cat.semCat.OUT  # ASSIGN PM

                # TODO maybe we need the comparator here
                self.compareSemCat(right.cat.semCat.IN, left.cat.semCat, parent)  # IMPORTANT
                right.cat.semCat.IN = left.cat.semCat

            elif parent.ruleType == 'bx':
                # two possibilities
                # X/Y Y\Z -> X\Z
                if parent.cat.direction == 'l':
                    # if left.cat.right.typeWOfeats == right.cat.left.typeWOfeats:
                    # make sure input and output of BX is correct
                    assert parent.cat.semCat.IN.semCatStr == right.cat.semCat.IN.semCatStr
                    assert parent.cat.semCat.OUT.semCatStr == left.cat.semCat.OUT.semCatStr
                    parent.cat.semCat.IN = right.cat.semCat.IN  # ASSIGN PM
                    parent.cat.semCat.OUT = left.cat.semCat.OUT  # ASSIGN PM
                    # TODO comparator here
                    self.compareSemCat(left.cat.semCat.IN, right.cat.semCat.OUT, parent)
                    left.cat.semCat.IN = right.cat.semCat.OUT

                # Y/Z X\Y -> X/Z
                else:
                    # make sure input and output of BX is correct
                    assert parent.cat.semCat.IN.semCatStr == left.cat.semCat.IN.semCatStr
                    assert parent.cat.semCat.OUT.semCatStr == right.cat.semCat.OUT.semCatStr
                    parent.cat.semCat.IN = left.cat.semCat.IN  # ASSIGN PM
                    parent.cat.semCat.OUT = right.cat.semCat.OUT  # ASSIGN PM
                    # TODO comparator here
                    self.compareSemCat(right.cat.semCat.IN, left.cat.semCat.OUT, parent)
                    right.cat.semCat.IN = left.cat.semCat.OUT

                # ASSIGN PM
                # if at least one of them is None (i.e. dot), result = None:
                if (right.cat.semCat.pm is None) or (left.cat.semCat.pm is None):
                    parent.cat.semCat.pm = None
                elif right.cat.semCat.pm == left.cat.semCat.pm:
                    parent.cat.semCat.pm = '+'
                else:
                    parent.cat.semCat.pm = '-'

            elif parent.ruleType == 'fc':
                # X/Y Y/Z -> X/Z
                if left.cat.right.typeWOfeats == right.cat.left.typeWOfeats:
                    # make sure input and output of fc is correct
                    assert parent.cat.semCat.IN.semCatStr == right.cat.semCat.IN.semCatStr
                    assert parent.cat.semCat.OUT.semCatStr == left.cat.semCat.OUT.semCatStr
                    parent.cat.semCat.IN = right.cat.semCat.IN  # ASSIGN PM
                    parent.cat.semCat.OUT = left.cat.semCat.OUT  # ASSIGN PM
                    # TODO comparator here
                    self.compareSemCat(left.cat.semCat.IN, right.cat.semCat.OUT, parent)
                    left.cat.semCat.IN = right.cat.semCat.OUT

                # Y\Z X\Y -> X\Z
                else:
                    assert parent.cat.semCat.IN.semCatStr == left.cat.semCat.IN.semCatStr
                    assert parent.cat.semCat.OUT.semCatStr == right.cat.semCat.OUT.semCatStr
                    parent.cat.semCat.IN = left.cat.semCat.IN  # ASSIGN PM
                    parent.cat.semCat.OUT = right.cat.semCat.OUT  # ASSIGN PM
                    # TODO comparator here
                    self.compareSemCat(right.cat.semCat.OUT, left.cat.semCat.IN, parent)
                    right.cat.semCat.OUT = left.cat.semCat.IN

                # ASSIGN PM
                # if at least one of them is None (i.e. dot), result = None:
                if (right.cat.semCat.pm is None) or (left.cat.semCat.pm is None):
                    parent.cat.semCat.pm = None
                elif right.cat.semCat.pm == left.cat.semCat.pm:
                    parent.cat.semCat.pm = '+'
                else:
                    parent.cat.semCat.pm = '-'

            elif parent.ruleType in ['rp', 'lp']:  # punctuation, make parent.pm = non-punctuation-child.pm
                if parent.cat.semCat.semCatStr == left.cat.semCat.semCatStr:
                    parent.cat.semCat.pm = left.cat.semCat.pm
                else:
                    parent.cat.semCat.pm = right.cat.semCat.pm

            elif parent.ruleType == 'conj':
                # dealt separately when traversing the tree for 2nd time
                # see getPM_NTNmyparentCONJ(),
                # here we only get the cat, and pm on the SLASHES, not on the NP
                if left.cat.typeWOfeats.upper() == 'CONJ':
                    rightType = right.cat.typeWOpolarity
                    left.cat = Cat('(' + rightType + '\\' + rightType + ')/' + rightType,
                                   word=left.word)

                    # assign pm to conj, both slashes are '+'
                    left.cat.semCat.pm = '+'
                    left.cat.semCat.OUT.pm = '+'
                    # assign pm to parent '+'
                    parent.cat.semCat.pm = '+'
                elif right.cat.typeWOfeats.upper() == 'CONJ':
                    leftType = left.cat.typeWOpolarity
                    right.cat = Cat('(' + leftType + '/' + leftType + ')\\' + leftType,
                                    word=right.word)

                    # assign pm to conj, both slashes are '+'
                    right.cat.semCat.pm = '+'
                    right.cat.semCat.OUT.pm = '+'
                    # assign pm to parent '+'
                    parent.cat.semCat.pm = '+'

            else:
                print('\nunable to process rule in getPM_NTN(): {}'.format(node.parent.ruleType))
                print(node)
                print(node.parent)
                pass

                # TODO
        else:
            print('wrong number of sisters: {}'.format(node))
            exit(1)

    def compareSemCat(self, semCat1, semCat2, parent):
        # true if semCat1 >= semCat2
        if semCat1.pm is None:
            return
        elif semCat1.pm != semCat2.pm:
            print('\n\ncompareSemCat not satisfied! see below')
            self.printTree()
            print(semCat1, semCat2)
            print(semCat1.pm, semCat2.pm)
            print('parent:', parent)
            print('\ncompareSemCat not satisfied! see above')
            exit(1)
        else:
            return

    def polarize(self):
        self.polarizeHelper(self.root, 'UP')

    def polarizeHelper(self, node, monoDirection):
        # assign UP/DOWN to node
        node.cat.monotonicity = monoDirection

        if len(node.children) == 0:  # leaf
            return
        if len(node.children) == 2:  # 2 children
            left = node.children[0]
            right = node.children[1]
            
            if node.ruleType == 'ba':  # Y X\Y --> X
                try:
                    if right.ruleType.upper() == 'CONJ':
                        self.polarizeHelper(left, self.calcMono(right, monoDirection))
                        self.polarizeHelper(right, monoDirection)
                    else:
                        if right.cat.semCat.IN.semCatStr == '((e,t),t)':  # NP
                            if right.cat.semCat.IN.pm == '-':  # NP-
                                # then flip monotonicity
                                self.polarizeHelper(right, self.flip(monoDirection))
                            elif right.cat.semCat.IN.pm is None:  # NP=
                                self.polarizeHelper(right, 'UNK')
                            else:  # NP+
                                self.polarizeHelper(right, monoDirection)
                        else:
                            self.polarizeHelper(right, monoDirection)
                        self.polarizeHelper(left, self.calcMono(right, monoDirection))
                except AttributeError: # 'LeafNode' object has no attribute 'ruleType'
                    if right.cat.semCat.IN.semCatStr == '((e,t),t)':  # NP
                        if right.cat.semCat.IN.pm == '-':  # NP-: K rule!
                            # then flip monotonicity
                            self.polarizeHelper(right, self.flip(monoDirection))
                        elif right.cat.semCat.IN.pm is None:  # NP=
                            self.polarizeHelper(right, 'UNK')
                        else:  # NP+
                            self.polarizeHelper(right, monoDirection)
                    else:
                        self.polarizeHelper(right, monoDirection)
                    self.polarizeHelper(left, self.calcMono(right, monoDirection))

                # # K rule:
                # print('\n\n-----right-----')
                # print(right)
                # print(right.cat.semCat.IN.semCatStr, right.cat.semCat.IN.pm)
                # if right.cat.semCat.IN.semCatStr == '((e,t),t)' and \
                #     right.cat.semCat.IN.pm == '-': # NP and -
                #     # then flip monotonicity
                #     print('flip!')
                #     self.flip(monoDirection)
                #     right.cat.monotonicity = self.calcMono('-', right.cat.monotonicity)
                # print('-----right-----\n\n')
            
            elif node.ruleType == 'fa':  # X/Y Y --> X
                try:
                    if left.ruleType.upper() == 'CONJ':
                        self.polarizeHelper(right, self.calcMono(left, monoDirection))
                        self.polarizeHelper(left, monoDirection)
                    else:
                        if left.cat.semCat.IN.semCatStr == '((e,t),t)':  # NP
                            if left.cat.semCat.IN.pm == '-':  # NP-
                                # then flip monotonicity
                                self.polarizeHelper(left, self.flip(monoDirection))
                            elif left.cat.semCat.IN.pm is None:  # NP=
                                self.polarizeHelper(left, 'UNK')
                            else:  # NP+
                                self.polarizeHelper(left, monoDirection)
                        else:
                            self.polarizeHelper(left, monoDirection)
                        self.polarizeHelper(right, self.calcMono(left, monoDirection))
                except AttributeError: # 'LeafNode' object has no attribute 'ruleType'
                    if left.cat.semCat.IN.semCatStr == '((e,t),t)':  # NP
                        if left.cat.semCat.IN.pm == '-':  # NP-
                            # then flip monotonicity
                            self.polarizeHelper(left, self.flip(monoDirection))
                        elif left.cat.semCat.IN.pm is None:  # NP=
                            self.polarizeHelper(left, 'UNK')
                        else:  # NP+
                            self.polarizeHelper(left, monoDirection)
                    else:
                        self.polarizeHelper(left, monoDirection)
                    self.polarizeHelper(right, self.calcMono(left, monoDirection))

            elif node.ruleType == 'bx':
                # X/Y Y\Z -> X\Z
                if left.cat.right.typeWOfeats == right.cat.left.typeWOfeats:
                    self.polarizeHelper(right, monoDirection)
                    self.polarizeHelper(left, self.calcMono(right, monoDirection))
                # Y/Z X\Y -> X/Z
                else:
                    self.polarizeHelper(left, monoDirection)
                    self.polarizeHelper(right, self.calcMono(left, monoDirection))

            elif node.ruleType == 'fc':  # X/Y Y/Z -> X/Z or Y\Z X\Y -> X\Z
                # X/Y Y/Z -> X/Z
                if left.cat.right.typeWOfeats == right.cat.left.typeWOfeats:
                    self.polarizeHelper(right, monoDirection)
                    self.polarizeHelper(left, self.calcMono(right, monoDirection))
                # Y\Z X\Y -> X\Z
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
                        print('unable to polarize conj rule!\nNo "CC" pos')
                except:
                    print('unable to polarize conj rule!\n')
                    print(left)
                    print(right)
                    exit(1)

            elif node.ruleType in ['rp', 'lp']: # punctuation
                self.polarizeHelper(left, monoDirection)
                self.polarizeHelper(right, monoDirection)

            else:
                print('unknown ruleType in polarize: {}'.format(node.ruleType))
                pass

        elif len(node.children) == 1:  # 1 child
            child = node.children[0]
            if node.ruleType == 'lex':
                self.polarizeHelper(child, monoDirection)
            elif node.ruleType == 'unlex':  # keep the same direction
                self.polarizeHelper(child, monoDirection)
            elif node.ruleType == 'tr':  # type raising
                # for (x->y)->y, the +/- on the first arrow
                # determines the monoDirection of child
                self.polarizeHelper(child,
                                    self.calcMono(node.cat.semCat.IN.pm, monoDirection))
            else:
                print('unknown ruleType in polarize: {}'.format(node.ruleType))
                pass

    def calcMono(self, functorORpm, monoDirection):
        ''' functorORpm can either be a functor or simply pm(+/-) '''
        pm = functorORpm
        if functorORpm not in ['-', '+', None]:
            pm = functorORpm.cat.semCat.pm

        if monoDirection == 'UP' and pm == '-':
            return 'DOWN'
        elif monoDirection == 'DOWN' and pm == '-':
            return 'UP'
        elif monoDirection == 'UP' and pm == '+':
            return 'UP'
        elif monoDirection == 'DOWN' and pm == '+':
            return 'DOWN'
        elif monoDirection == 'UNK' or pm is None:  # None = 'dot':
            return 'UNK'
        else:
            self.printTree()
            print(pm, monoDirection)
            sys.exit('Unknown Mono monoDirection/functor!')

    def flip(self, monoDirection):
        ''' flip UP and DOWN'''
        if monoDirection == 'UP':
            return 'DOWN'
        elif monoDirection == 'DOWN':
            return 'UP'
        else:
            return 'UNK'

    def build(self, ccgXml):
        ''' build the tree recursively from xml output of CandC '''
        self.root = NonTermNode(depth=-1)  # dummy root; important
        self.buildHelper(ccgXml, self.root, -1)
        self.getWholeStrAllNodes()
        # allNodes
        self.allNodes = self.leafNodes + self.nonTermNodes

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
            nodeMostNew.cat.semCat.OUT.pm = '+'
            nodeMostNew.cat.semCat.pm = None
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
                 B               getLeftMostLeaf(B) will return X
        '''
        while len(node.children) != 0:
            # print(len(node.children))
            node = node.children[0]
        return node

    def decreaseDepth(self, node):
        node.depth -= 1
        if len(node.children) == 0:
            return
        else:
            for n in node.children:
                self.decreaseDepth(n)

    def buildHelper(self, nodeXml, Node, depth):
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
                self.buildHelper(childXml,childNode,depth+1)

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
    def copy(self):
        cat = copy.deepcopy(self.cat) # recursively create new copy
        return LeafNode(self.depth,cat,self.chunk,self.entity,self.lemma,
                        self.pos,self.span,self.start,self.word)
    def __str__(self):
        return "lf: {} {} {} {} {}".format(self.cat,self.cat.semCat,self.word,self.depth,self.cat.monotonicity)
    def __repr__(self):
        return "lf: {} {} {} {} {}".format(self.cat,self.cat.semCat,self.word,self.depth,self.cat.monotonicity)

class NonTermNode():
    def __init__(self,depth=None,cat=None,ruleType=None,wholeStr=''):
        self.parent = None; self.children = []; self.sisters = []
        self.depth = depth
        self.cat = cat; self.ruleType = ruleType
        self.wholeStr = wholeStr
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
        return "nt: {} {} {} {} {}".format(self.cat,self.cat.semCat,self.ruleType,self.depth,self.cat.monotonicity)
    def __repr__(self):
        return "nt: {} {} {} {} {}".format(self.cat,self.cat.semCat,self.ruleType,self.depth,self.cat.monotonicity)

class SemCat():
    def __init__(self, semCatStr=None, IN=None, OUT=None, pm=None): # '+'):
        # TODO initialize pm as '+' or None?
        ''' if it's just e or t, then it will be assigned to OUT, and IN=None;
        that is, there are only two basic SemCat: e and t
        all the others are built recursively based on these two '''
        self.IN = IN # (e,t): also a SemCat
        self.OUT = OUT # t: also a SemCat
        self.pm = pm # + or -, similar to lex_polarity
        if semCatStr:
            self.semCatStr = semCatStr # string: e.g. NP has sem cat: ((e,t),t)
        else:
            self.semCatStr = '({},{})'.format(self.IN, self.OUT)
            self.semCatStr = self.semCatStr.replace('-','').replace('+','')  # does NOT include -/+
    def assignRecursive(self, plusORminus):
        ''' assign +/- recursively to every --> inside '''
        self.assignRecursiveHelper(self, plusORminus)
    def assignRecursiveHelper(self, semcat, plusORminus):
        if semcat is None:
            return
        else:
            print(semcat)
            semcat.pm = plusORminus
            self.assignRecursiveHelper(semcat.IN, plusORminus)
            self.assignRecursiveHelper(semcat.OUT, plusORminus)
    def __str__(self):
        if (self.IN is None) and (self.OUT is None):
            return '{}'.format(self.semCatStr)
        if self.pm:
            return '({},{}{})'.format(self.IN, self.pm, self.OUT)
        return '({},{})'.format(self.IN, self.OUT)
    def __repr__(self):
        if (self.IN is None) and (self.OUT is None):
            return '{}'.format(self.semCatStr)
        if self.pm:
            return '({},{}{})'.format(self.IN, self.pm, self.OUT)
        return '({},{})'.format(self.IN, self.OUT)

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
        self.direction = None  # \=l, /=r and s(single)
        self.left = None
        self.right = None
        self.originalType = None # (S\+NP)/+NP as a string, or NP[nb]/N
        self.typeWOpolarity = None # (S\NP)/NP as a string
        self.typeWOfeats = None # get rid of extra features like [nb]: NP/N
        self.monotonicity = None # [UP, DOWN]
        self.lex_polarity = None # [i, r], c.f. van Eijck's algorithm
        self.word = word # if it's the cat of a leafNode, then it has word
        # ------- SEMANTIC CAT ------- #
        self.semCat = SemCat()
        # ------- END: SEMANTIC CAT ------- #
        if originalType:
            self.originalType = originalType
        else: # a null Cat
            return
        if ('/' not in self.originalType) and ('\\' not in self.originalType):
            self.processBasicType()
        else:
            self.processComplexType()

        self.typeWOpolarity = self.originalType.replace('_i','').replace('_r','')
        self.typeWOfeats = re.sub('\[\w+?\]','',self.typeWOpolarity)
        if self.semCat.semCatStr == '(((e,t),t),t)':
            self.semCat.pm = '+'

    def processBasicType(self):
        ''' basicType: NP, S, N. I.e. with out slashes '''
        self.direction = 's'
        self.left = self.right = None
        self.typeWOpolarity = self.originalType.replace('_i','').replace('_r','')
        self.originalType = self.typeWOpolarity
        # ------- SEMANTIC CAT ------- #
        # can only be S, N, NP
        self.typeWOfeats = re.sub('\[\w+?\]','',self.typeWOpolarity)
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

        elif self.typeWOfeats.upper() in ['.',',']:
            self.semCat = SemCat()

        elif self.typeWOfeats.upper() == 'PP': # TODO
            self.semCat = SemCat(**{'semCatStr':'pp'})

        elif self.typeWOfeats.upper() == 'CONJ': # TODO
            if self.word.upper() == 'AND': # TODO ?? and is +?
                self.semCat = SemCat(**{'semCatStr':'CONJ','pm':'+'})
            elif self.word.upper() == 'OR':
                self.semCat = SemCat(**{'semCatStr':'CONJ','pm':'+'})
            elif self.word.upper() == 'BUT':
                self.semCat = SemCat(**{'semCatStr':'CONJ','pm':'-'})
            else:
                print('unable to create semCat for conjunction {}'.format(self.word))

        else:
            self.semCat = SemCat()
            print('no semCat for basic type: {}'.format(self.typeWOfeats))
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

            if ind1 == -1 and ind2 != -1: # only has /
                self.direction = 'r'  # right
                ind = ind2
            elif ind2 == -1 and ind1 != -1: # only has \
                self.direction = 'l'  # left
            else:  # has both / and \
                if ind2 < ind1: # first slash is /
                    ind = ind2
                    self.direction = 'r'

            # now ind is the critical slash that separates left and right
            try:
                if self.originalType[(ind-2):ind] in ['_i','_r']:
                    self.lex_polarity = self.originalType[(ind-1):ind]
            except IndexError:
                pass
            self.left = self.originalType[:ind]
            right_tmp = self.originalType[(ind + 1):]

            right_tmp = self.stripOneChar(right_tmp, '(')
            self.right = self.stripOneChar(right_tmp, ')')

        # if the left part has brackets: e.g. ((XP\X)/XP)\(((X\Y)/Z)\A)
        else:
            numLB = 1  # number of left brackets '('
            ind = 1 # the index for / or \

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
            except:
                pass

            if self.originalType[ind] == '\\':
                self.direction = 'l'
            elif self.originalType[ind] == '/':
                self.direction = 'r'
            else:
                print('something went wrong when converting types!')
                print(self.originalType, self.originalType[ind])
                exit(1)

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

        # if the word is 'who', then assign '+' to every slash
        if (self.word is not None)\
                and (self.word.upper() in ['WHO', 'THAT', 'WHICH']):
            # print('here')
            self.semCat = SemCat(**{'IN': self.right.semCat,
                                    'OUT': self.left.semCat, 'pm':'+'})
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

if __name__ == '__main__':
    main()
