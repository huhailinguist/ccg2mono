#!/usr/bin/env python3
'''
get inference

input: polarized trees from getMono.py

Hai Hu, Feb 2018
'''

import getMono
import sys, re, os, copy

def main():
    sentToTest = None
    if len(sys.argv) >= 2:
        sentToTest = int(sys.argv[1]) # sentence to test
        print('sentToTest:',sentToTest)
    trees = getMono.CCGtrees()
    trees.readCandCxml('tmp.candc.xml')

    # build knowledge
    k = buildKnowledge() # THIS IS DONE April 26

    # TODO read in sent, do replacement

    print()
    print('-' * 20)
    t = trees.trees[0]
    if any(x in sys.argv for x in ['-v1', '-vall']):
        t.printTree()
    t.getPM()
    if any(x in sys.argv for x in ['-v2', '-vall']):
        t.printTree()
    t.polarize()
    if any(x in sys.argv for x in ['-v3', '-vall']):
        t.printTree()
    t.printSent()

    # ---------------------------
    # now replacement
    print('\nNOW REPLACEMENT\n')
    t.replacement(k=k)
    print('\nwe can infer:')
    for i in t.inferences:
        i.replacement(k=k)
        for j in i.inferences:
            j.replacement(k=k)

    t.printAllInferences()


    # getInferOld(t, conc='No historian catwalks .')

'''
Pipeline:

wordnet/sentences => our representation => replacement

Now we just assume we already have our representation.
In the next step, we start with wordnet/sentences

===================
Our representation (Knowledge class):

- big dogs < large animals

Both phrases should be trees. I.e. the CCGtree class from getMono.py

big   dogs
N/N   N
---------- fa
    N

===================
Replacement:

- Find in the premise a node N 1) with string 'big dogs' and
2) with the same tree structure (?this will be hard to do)

- Replace N with the node 'large animals'

We should loop every node in CCGtree.

===================
Test:
- premise: Every large animal likes vegetables.
- conc: Every big dog likes carrots.


'''

def buildKnowledge():
    print('\n\n-----------\nbuilding knowledge...')
    k = Knowledge()

    '''
    I chased some cat.
    I hit every bird.
    I see some animal.
    It is black.

    chased some cat < liked every dog (small1, big1)
    see some animal < is black (small2, big2)
    old dog < dog (small3, big3)
    young man < man (s4, b4)
    cat < animal (s5, b5)
    every man < John < some man (s6, m6, b6)
    '''

    knowledgeTrees = getMono.CCGtrees()
    knowledgeTrees.readCandCxml('knowledge.candc.xml')

    # ----------------------
    small1 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[0].root.children[0].children[1]
    )
    print(small1.wholeStr)

    big1 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[1].root.children[0].children[1]
    )
    print(big1.wholeStr)

    # ----------------------
    small2 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[2].root.children[0].children[1]
    )
    print(small2.wholeStr)

    big2 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[3].root.children[0].children[1]
    )
    print(big2.wholeStr)

    # ----------------------
    small3 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[4].root.children[0].children[1]
    )
    print(small3.wholeStr)

    big3 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[5].root.children[0].children[1]
    )
    print(big3.wholeStr)

    # ----------------------
    s4 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[0].root.children[0].children[1].children[1].children[1]
    )
    print(s4.wholeStr)  # cat

    b4 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[6].root.children[0].children[1]
    )
    print(b4.wholeStr)  # animal

    # ----------------------
    s5 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[7].root.children[0].children[1]
    )
    print(s5.wholeStr)  # young man

    b5 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[7].root.children[0].children[1].children[1]
    )
    print(b5.wholeStr)  # man

    # ----------------------
    s6 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[8].root.children[0].children[0]
    )
    print(s6.wholeStr)  # every man

    m6 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[9].root.children[0].children[0]
    )
    print(m6.wholeStr)  # John

    b6 = getMono.CCGtree(
        NonTermNode=knowledgeTrees.trees[10].root.children[0].children[0]
    )
    print(b6.wholeStr)  # some man

    # add to knowledge
    k.addFrag((small1, big1))
    k.addFrag((small2, big2))
    k.addFrag((small3, big3))
    k.addFrag((s4, b4))
    k.addFrag((s5, b5))
    k.addFrag((s6, m6))
    k.addFrag((m6, b6))
    k.addFrag((s6, b6))

    print('\nknowledge built!\n--------------\n')
    return k

class Knowledge:
    def __init__(self):
        self.frags = {}  # TODO should we call them preorders?
        # key is string, value is Fragment class
        self.numPairs = 0
    def addFrag(self, pair):  # pair is a tuple = (small, big)
        small = pair[0]  # a CCGtree
        big = pair[1]  # a CCGtree

        # add big to self.frags[small.wholeStr]
        if small.wholeStr not in self.frags.keys():
            smallAsFrag = Fragment(small)
            smallAsFrag.big.append(Fragment(big))
            smallAsFrag.wholeStr = small.wholeStr
            self.frags[small.wholeStr] = smallAsFrag

        if small.wholeStr in self.frags.keys():
            if big.wholeStr not in [x.wholeStr for x in self.frags[small.wholeStr].big]:
                self.frags[small.wholeStr].big.append(Fragment(big))

        # add small to self.frags[big.wholeStr]
        if big.wholeStr not in self.frags.keys():
            bigAsFrag = Fragment(big)
            bigAsFrag.small.append(Fragment(small))
            bigAsFrag.wholeStr = big.wholeStr
            self.frags[big.wholeStr] = bigAsFrag

        if big.wholeStr in self.frags.keys():
            if small.wholeStr not in [x.wholeStr for x in self.frags[big.wholeStr].small]:
                self.frags[big.wholeStr].small.append(Fragment(small))

        self.numPairs += 1

class Fragment:
    def __init__(self, ccgtree=None):
        '''  small < frag < big;  a frag could be "chased some cat"  '''
        self.ccgtree = ccgtree  # a CCGtree
        self.wholeStr = ccgtree.wholeStr  # 'CHASED SOME CAT'
        self.small = []  # could have multiple small
        self.big = []  # could have multiple big
    def __str__(self):
        return '{}'.format(self.wholeStr)
    def __repr__(self):
        return self.__str__()

class Pair:
    ''' each pair is a relation: big dogs < large animals
        small = big dogs; big = large animals
    '''
    def __init__(self, small, big):  # small and big are CCGtrees
        self.small = small
        self.big = big

def getInferOld(CCGtree, premises=None, conc=None):
    # parse conclusion
    wordsRelevant = set()
    if premises:
        wordsRelevant.update( set(p.split(' ')) for p in premises )
    if conc:
        wordsRelevant.update( set(p.split(' ')) for p in conc )

    # make a new tree
    newTree = copy.deepcopy(CCGtree)

    for leafN in newTree.leafNodes:
        # nouns, verbs
        if leafN.pos[0].upper() in ['N', 'V']:
            print()
            if leafN.cat.monotonicity == 'UP':
                print('UP for:', leafN)
                # print(WN.getHypernyms(leafN.word, pos='n'))
                hyps = WN.getAllHyps('hypernym', leafN.word, pos='n')
                for hyp in hyps:
                    if hyp in wordsRelevant:
                        print(hyp)

            elif leafN.cat.monotonicity == 'DOWN':
                print('DOWN for:', leafN)
                # print(WN.getHyponyms(leafN.word, pos='n'))
                hyps = WN.getAllHyps('hyponym', leafN.word, pos='n')
                for hyp in hyps:
                    if hyp in wordsRelevant:
                        print(hyp)

if __name__ == '__main__':
    main()

