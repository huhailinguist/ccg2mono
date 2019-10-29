import argparse
import xml.etree.ElementTree as ET

""" Takes a polarity-labeled xml file from parse.sh and outputs tokenized
strings followed by the polarity labels for those tokens. """

polarity_to_labels = {
    '\u2191': 'UP',
    '\u2193': 'DOWN',
    '=': 'NEUTRAL'
}

def main(args):

    tree = ET.parse(args.in_file)
    root = tree.getroot()

    for sentence in root.iter('sentence'):
        tokens = list(sentence.iter('token'))
        string = ' '.join([token.attrib['surf'] for token in tokens])
        polarity = ' '.join([polarity_to_labels[token.attrib['polarity']] for token in tokens])
        print(string)
        print(polarity)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--in_file', '-i', type=str)
    args = parser.parse_args()

    main(args)
