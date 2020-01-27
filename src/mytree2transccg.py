#!/usr/bin/env python3
"""
convert trees in my data structure to transccg, then we can
use ${ccg2lambdaDir}/scripts/visualize.py to output an .html file
for pretty viewing.

Aug, 2018

TODO: what is transccg?
"""

__author__ = "Hai Hu"

from getMono import CCGtree, CCGtrees, ErrorCCGtree, ErrorCompareSemCat, eprint, ErrorCat
import sys

# <token start="0" span="1" pos="DT" chunk="I-NP" entity="O" cat="NP[nb]/N" id="t0_0" surf="Every" base="every" ETtype="None" polarity="None"/>
str_token = '<token start="{}" span="{}" pos="{}" chunk="{}" entity="{}" ' \
          'cat="{}" id="{}" surf="{}" base="{}" ETtype="{}" polarity="{}"/>'

# <span start="0" span="1" pos="DT" chunk="I-NP" entity="O" id="s0_sp4" surf="Every" base="every" terminal="t0_0" category="NP[nb=true]/N" ETtype="None" polarity="None"/>
str_span_leaf = '<span start="{}" span="{}" pos="{}" chunk="{}" entity="{}" ' \
              'id="{}" surf="{}" base="{}" terminal="{}" category="{}" ETtype="{}" polarity="{}"/>'

# <span root="true" id="s0_sp0" child="s0_sp1 s0_sp16" pos="None" category="S[dcl=true]" rule="rp" ETtype="None" polarity="None"/>
str_span_root = '<span root="true" id="{}" child="{}" pos="None" ' \
              'category="{}" rule="{}" ETtype="{}" polarity="{}"/>'

# <span id="s0_sp1" child="s0_sp2 s0_sp13" pos="None" category="S[dcl=true]" rule="ba" ETtype="None" polarity="None"/>
str_span_nonTerm = '<span id="{}" child="{}" pos="None" category="{}" ' \
                 'rule="{}" ETtype="{}" polarity="{}"/>'

message = "\nUsage: ./mytree2transccg.py filename parser filename_log\n" \
          "e.g. filename=test.easyccg.parsed.txt,\n" \
          "filename_log=test.tok.preprocess.log\n"

def main():
    if len(sys.argv) < 4:
        eprint(message)
    else:
        filename = sys.argv[1]
        parser = sys.argv[2]
        filename_log = sys.argv[3]
        convert2transccg(filename, parser, filename_log)

def convert2transccg(filename, parser, filename_log):
    """
    input: 
    - easyccg output (tmp.easyccg.parsed.txt) or 
    - candc output (tmp.candc.parsed.xml)

    input is read into my CCGtree format. 

    then traverse the tree and print xml to stdout

    return # of sents not polarized
    """
    trees = CCGtrees(filename_log)
    
    if parser == 'easyccg':
        trees.readEasyccgStr(filename)  #('tmp.easyccg.parsed.txt')
        raw_sentences = open(filename.replace(".easyccg.parsed.txt","") + ".tok.clean").readlines()
    elif parser == 'candc':
        trees.readCandCxml(filename)  #('tmp.candc.parsed.xml')
        raw_sentences = open(filename.replace(".candc.parsed.xml","") + ".tok.clean").readlines()
    elif parser == 'depccg':  # same as easyccg
        trees.readEasyccgStr(filename)  
        raw_sentences = open(filename.replace(".depccg.parsed.txt","") + ".tok.clean").readlines()
    else:
        eprint('parser can only be: easyccg, candc, depccg')
        exit()

    # ----------------------------------
    # mark and polarize
    N_polar = 0
    N_unpolar = 0
    N_unparsed = 0
    fh_polarized_trees = open(filename + ".polarized", "w")

    # sent_parsed = True

    # idx_cant_polarize = {}
    for idx in range(len(raw_sentences)):
        # build the tree here
        t = trees.build_one_tree(idx, parser, use_lemma=False)
        # eprint(trees.easyccg_str.get(idx, None))
        # print(t)
        # return

        if t in ["failed_to_parse", "parse_exception"]:  # easyccg failed to parse the sent
            eprint('easyccg failed to parse the sent')
            eprint(raw_sentences[idx])
            sent = raw_sentences[idx].replace(" ", "= ").replace("\n", "=\n")  # = for every token
            fh_polarized_trees.write(sent)
            N_unparsed += 1

        else:  # t is a tree
            # fix tree
            t.fixQuantifier()
            try: t.fixNot()
            except AttributeError: pass
            if parser in ['candc']: t.fixRC()  # only fix RC for candc

            try:
                t.mark()
                t.polarize()
                t.getImpSign()
                N_polar += 1
            except (ErrorCompareSemCat, ErrorCCGtree, AssertionError, AttributeError, ErrorCat) as e:
                eprint(e)
                eprint('-- cannot polarize sent: ', end='')
                N_unpolar += 1
            # t.printSent(stream=sys.stderr)
            fh_polarized_trees.write(t.printSent_raw(stream=sys.stderr))
            fh_polarized_trees.write("\n")
        eprint()
    fh_polarized_trees.close()
    eprint("\n\n===========\npolarized {} trees\n"
           "unable to parse {} trees\n"
           "unable to polarize {} trees".format(N_polar, N_unparsed, N_unpolar))

    # ----------------------------------

    print("""<?xml version='1.0' encoding='UTF-8'?>\n<root>\n<document>\n<sentences>""")
    for idx, t in trees.trees.items():
        if t in ["failed_to_parse", "parse_exception"]:
            continue

        print("<sentence>")

        # ----------------------------
        # print tokens
        print("<tokens>")
        counter = 0
        for token in t.leafNodes:
            # depth,cat,chunk,entity,lemma,pos,span,start,word
            token_id = "t"+str(idx)+'_'+str(counter)
            ETtype = token.cat.semCat.__str__()
            polarity = getPolarityAsArrow(token)
            print(str_token.format(token.start, token.span, token.pos, token.chunk,
                                 token.entity, token.cat.originalType, token_id,
                                 token.word, token.lemma, ETtype, polarity))
            counter += 1
        print("</tokens>")

        # ----------------------------
        # print nodes
        # <ccg root="s0_sp0" id="s0_ccg0">
        print('<ccg root="s{}_sp0" id="s{}_ccg0">'.format(str(idx), str(idx)))

        # tree
        # in-order traversal of tree to get span_id of non term node
        traverse2get_span_id(t.root, -1, idx)

        # in order traversal of tree
        traverse(t.root, 0, idx)

        print("</ccg>")
        print("</sentence>")

    print("""</sentences>\n</document>\n</root>""")


def traverse2get_span_id(node, counter, idx):
    '''
    traverse the tree to get span_id of all nodes (leaf + non term)
    '''
    counter += 1
    if node is None: return  # why would this happen?

    # idx is the sentence idx
    if len(node.children) == 0:  # leaf
        node.span_id = 's' + str(idx) + '_sp' + str(counter)
    elif len(node.children) == 1:  # 1 child
        node.span_id = 's' + str(idx) + '_sp' + str(counter)
        counter = traverse2get_span_id(node.children[0], counter, idx)
    else:  # 2 children
        node.span_id = 's' + str(idx) + '_sp' + str(counter)
        counter = traverse2get_span_id(node.children[0], counter, idx)
        counter = traverse2get_span_id(node.children[1], counter, idx)
    return counter

def traverse(node, leafCounter, idx):
    """ traverse the tree to print xml """
    ETtype = node.cat.semCat.__str__()
    polarity = getPolarityAsArrow(node)
    if node.impSign:  # TODO need to fix this
        polarity = polarity + " : " + node.impSign  # plus implicative sign

    if len(node.children) == 0:  # leaf
        terminal = "t"+str(idx)+'_'+str(leafCounter)
        print(str_span_leaf.format(node.start, node.span, node.pos,
                                 node.chunk, node.entity, node.span_id,
                                 node.word, node.lemma, terminal,
                                 node.cat.originalType, ETtype, polarity))
        leafCounter += 1

    else:
        child_str = ' '.join(child.span_id for child in node.children)
        # 1 child
        if len(node.children) == 1:
            # root
            if node.span_id[3:] == 'sp0':
                child_str = ' '.join(child.span_id for child in node.children)
                print(str_span_root.format(node.span_id, child_str, node.cat.originalType, node.ruleType, ETtype, polarity))
            else:
                print(str_span_nonTerm.format(node.span_id, child_str, node.cat.originalType, node.ruleType, ETtype, polarity))

            leafCounter = traverse(node.children[0], leafCounter, idx)

        # 2 children
        else:
            # root
            if node.span_id[3:] == 'sp0':
                child_str = ' '.join(child.span_id for child in node.children)
                print(str_span_root.format(node.span_id, child_str, node.cat.originalType, node.ruleType, ETtype, polarity))
            else:
                print(str_span_nonTerm.format(node.span_id, child_str, node.cat.originalType, node.ruleType, ETtype, polarity))
            
            leafCounter = traverse(node.children[0], leafCounter, idx)
            leafCounter = traverse(node.children[1], leafCounter, idx)

    return leafCounter

def getPolarityAsArrow(node):
    """ map (None, UP, DOWN) to (=, uparrow, downarrow) """
    polarity = "="
    if node.cat.monotonicity == "UP": polarity = '\u2191'
    elif node.cat.monotonicity == "DOWN": polarity = '\u2193'
    return polarity

if __name__ == '__main__':
    main()

# desired xml output:
r"""
<?xml version='1.0' encoding='UTF-8'?>
<root>
  <document>
    <sentences>
      <sentence>
        <tokens>
          <token start="0" span="1" pos="DT" chunk="I-NP" entity="O" cat="NP[nb]/N" id="t0_0" surf="Every" base="every"/>
          <token start="1" span="1" pos="NN" chunk="I-NP" entity="O" cat="N" id="t0_1" surf="man" base="man"/>
          <token start="2" span="1" pos="WP" chunk="B-NP" entity="O" cat="(NP\NP)/(S[dcl]\NP)" id="t0_2" surf="who" base="who"/>
          <token start="3" span="1" pos="VBZ" chunk="I-VP" entity="O" cat="(S[dcl]\NP)/NP" id="t0_3" surf="speaks" base="speak"/>
          <token start="4" span="1" pos="DT" chunk="I-NP" entity="O" cat="NP[nb]/N" id="t0_4" surf="some" base="some"/>
          <token start="5" span="1" pos="NN" chunk="I-NP" entity="O" cat="N" id="t0_5" surf="language" base="language"/>
          <token start="6" span="1" pos="VBZ" chunk="I-VP" entity="O" cat="(S[dcl]\NP)/NP" id="t0_6" surf="reads" base="read"/>
          <token start="7" span="1" pos="PRP" chunk="I-NP" entity="O" cat="NP" id="t0_7" surf="it" base="it"/>
          <token start="8" span="1" pos="." chunk="O" entity="O" cat="." id="t0_8" surf="." base="."/>
        </tokens>
        <ccg root="s0_sp0" id="s0_ccg0">
          <span root="true" id="s0_sp0" child="s0_sp1 s0_sp16" pos="None" category="S[dcl=true]" rule="rp"/>
          <span id="s0_sp1" child="s0_sp2 s0_sp13" pos="None" category="S[dcl=true]" rule="ba"/>
          <span id="s0_sp2" child="s0_sp3 s0_sp6" pos="None" category="NP" rule="ba"/>
          <span id="s0_sp3" child="s0_sp4 s0_sp5" pos="None" category="NP[nb=true]" rule="fa"/>
          <span start="0" span="1" pos="DT" chunk="I-NP" entity="O" id="s0_sp4" surf="Every" base="every" terminal="t0_0" category="NP[nb=true]/N"/>
          <span start="1" span="1" pos="NN" chunk="I-NP" entity="O" id="s0_sp5" surf="man" base="man" terminal="t0_1" category="N"/>
          <span id="s0_sp6" child="s0_sp7 s0_sp8" pos="None" category="NP\NP" rule="fa"/>
          <span start="2" span="1" pos="WP" chunk="B-NP" entity="O" id="s0_sp7" surf="who" base="who" terminal="t0_2" category="(NP\NP)/(S[dcl=true]\NP)"/>
          <span id="s0_sp8" child="s0_sp9 s0_sp10" pos="None" category="S[dcl=true]\NP" rule="fa"/>
          <span start="3" span="1" pos="VBZ" chunk="I-VP" entity="O" id="s0_sp9" surf="speaks" base="speak" terminal="t0_3" category="(S[dcl=true]\NP)/NP"/>
          <span id="s0_sp10" child="s0_sp11 s0_sp12" pos="None" category="NP[nb=true]" rule="fa"/>
          <span start="4" span="1" pos="DT" chunk="I-NP" entity="O" id="s0_sp11" surf="some" base="some" terminal="t0_4" category="NP[nb=true]/N"/>
          <span start="5" span="1" pos="NN" chunk="I-NP" entity="O" id="s0_sp12" surf="language" base="language" terminal="t0_5" category="N"/>
          <span id="s0_sp13" child="s0_sp14 s0_sp15" pos="None" category="S[dcl=true]\NP" rule="fa"/>
          <span start="6" span="1" pos="VBZ" chunk="I-VP" entity="O" id="s0_sp14" surf="reads" base="read" terminal="t0_6" category="(S[dcl=true]\NP)/NP"/>
          <span start="7" span="1" pos="PRP" chunk="I-NP" entity="O" id="s0_sp15" surf="it" base="it" terminal="t0_7" category="NP"/>
          <span start="8" span="1" pos="." chunk="O" entity="O" id="s0_sp16" surf="." base="." terminal="t0_8" category="."/>
        </ccg>
      </sentence>
    </sentences>
  </document>
</root>
"""
