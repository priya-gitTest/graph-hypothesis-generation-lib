# @name: hypothesis.py
# @description: Module for hypothesis generation
# @author: Núria Queralt Rosinach
# @date: 02-24-2018
# @version: 2.0

# This module is v2.0 because it is integrated with the rest of the graph library.
# This module reproduces orthopheno query on ngly1 graph created in the pipeline:
#      Database: neo4j-animal-v3 (localhost: http-7476, bolt-7689)
#      Seed: 'HGNC:17646','HGNC:633'  # HGNC ID scheme DOES NOT WORK
#      Query: clean orthopheno query
#      Output: json in hypothesis/ directory
#      PROBLEM: concept type
#      Sanity check:

# to dos:
#   * add check function to ensure that neo4j is up after import
#   * add check function to ensure that a query does not kill neo4j and that is up
#   * clean query (eliminate g1, ..)
#   * document the module
"""Module for hypothesis generation"""

from neo4j.v1 import GraphDatabase, basic_auth
#import argparse
import sys,os
import json
import yaml
import datetime
import neo4j.exceptions


# VARIABLES
today = datetime.date.today()


def parse_path( path ):
    """This function parses neo4j results."""

    out = {}
    out['Nodes'] = []
    for node in path['path'].nodes:
        n = {}
        n['idx'] = node.id
        n['label'] = list(node.labels)[0]
        n['id'] = node.properties['id']
        n['preflabel'] = node.properties['preflabel']
        n['description'] = node.properties['description']
        out['Nodes'].append(n)
    out['Edges'] = []
    for edge in path['path'].relationships:
        e = {}
        e['idx'] = edge.id
        e['start_node'] = edge.start
        e['end_node'] = edge.end
        e['type'] = edge.type
        e['preflabel'] = edge.properties['property_label']
        e['references'] = edge.properties['reference_uri']
        out['Edges'].append(e)
    return out


def query(genelist, queryname='', pwdegree='50', phdegree='20', format='json', port='7687'):
    """This function queries the graph database."""

    # initialize neo4j
    try:
        driver = GraphDatabase.driver("bolt://localhost:{}".format(port), auth=("neo4j", "xena"))
    except neo4j.exceptions.ServiceUnavailable:
        raise

    # query topology
    query_topology = """
    (source:GENE)-[:`RO:HOM0000020`]-(:GENE)--(ds:DISO)--(:GENE)-[:`RO:HOM0000020`]-(:GENE)--(pw:PHYS)--(target:GENE)
    """

    # ask the driver object for a new session
    with driver.session() as session:
        # create outdir
        if not os.path.isdir('./hypothesis'): os.makedirs('./hypothesis')
        sys.path.insert(0, '.')

        # output filename
        filename = 'query_{}_pwdl{}_phdl{}_paths_v{}'.format(queryname, pwdegree, phdegree, today)

        # run query
        outputAll = list()
        for gene1 in genelist:
            for gene2 in genelist:
                if gene2 == gene1:
                    continue
                source = gene1
                target = gene2
                query = """
                MATCH path=""" + query_topology + """
                MATCH (source { id: '""" + source + """'}), (target { id: '""" + target + """'})
                // no loops or only one pass per node
                WHERE ALL(x IN nodes(path) WHERE single(y IN nodes(path) WHERE y = x))
                WITH ds, pw, path,
                     // count node degree
                     max(size( (pw)-[]-() )) AS pwDegree,
                     max(size( (ds)-[]-() )) AS dsDegree,
                     // mark general nodes to filter path that contain them out
                     [n IN nodes(path) WHERE n.preflabel IN ['cytoplasm','cytosol','nucleus','metabolism','membrane','protein binding','visible','viable','phenotype']] AS nodes_marked,
                     // mark promiscuous edges to filter path that contain them out,
                     [r IN relationships(path) WHERE r.property_label IN ['interacts with','in paralogy relationship with','in orthology relationship with','colocalizes with']] AS edges_marked
                // condition to filter paths that do contain marked nodes and edges out
                WHERE size(nodes_marked) = 0 AND size(edges_marked) = 0 AND pwDegree <= """ + pwdegree + """ AND dsDegree <= """ + phdegree + """
                RETURN path
                """
                result = session.run(query)
                pair = {}
                pair['source'] = source
                pair['target'] = target
                # parse query results
                output = list()
                counter = 0
                for record in result:
                    path_dct = parse_path(record)
                    output.append(path_dct)
                    counter += 1
                    if (counter % 100000 == 0):
                        sys.stderr.write("Processed " + str(counter) + "\n")
                pair['paths'] = output
                outputAll.append(pair)

                # print output
                if (format == "yaml"):
                    print(yaml.dump(outputAll, default_flow_style=False))
                elif (format == "json"):
                    with open('./hypothesis/{}.json'.format(filename), 'w') as f:
                        json.dump(outputAll, f)
                    # print(json.dumps(outputAll))
                else:
                    sys.stderr.write("Error.\n")

    return sys.stderr.write("\nHypothesis generator has finished. {} QUERIES completed.\n".format(len(outputAll)))

def open_query(genelist, queryname='', format='json', port='7687'):
    """This function performs open queries to the graph database."""

    # initialize neo4j
    try:
        driver = GraphDatabase.driver("bolt://localhost:{}".format(port), auth=("neo4j", "xena"))
    except neo4j.exceptions.ServiceUnavailable:
        raise

    # query topology
    query_topology = """
    (source:GENE)-[:`RO:HOM0000020`]-(:GENE)--(:DISO)--(:GENE)-[:`RO:HOM0000020`]-(:GENE)--(:PHYS)--(target:GENE)
    """

    # ask the driver object for a new session
    with driver.session() as session:
        # create outdir
        if not os.path.isdir('./hypothesis'): os.makedirs('./hypothesis')
        sys.path.insert(0, '.')

        # output filename
        filename = 'query_{}_paths_v{}'.format(queryname, today)

        # run query
        outputAll = list()
        for gene1 in genelist:
            for gene2 in genelist:
                if gene2 == gene1:
                    continue
                source = gene1
                target = gene2
                query = """
                MATCH path=""" + query_topology + """
                MATCH (source { id: '""" + source + """'}), (target { id: '""" + target + """'})
                // no loops or only one pass per node
                //WHERE ALL(x IN nodes(path) WHERE single(y IN nodes(path) WHERE y = x))
                RETURN path
                """
                result = session.run(query)
                pair = {}
                pair['source'] = source
                pair['target'] = target
                # parse query results
                output = list()
                counter = 0
                for record in result:
                    path_dct = parse_path(record)
                    output.append(path_dct)
                    counter += 1
                    if (counter % 100000 == 0):
                        sys.stderr.write("Processed " + str(counter) + "\n")
                pair['paths'] = output
                outputAll.append(pair)

                # print output
                if (format == "yaml"):
                    print(yaml.dump(outputAll, default_flow_style=False))
                elif (format == "json"):
                    with open('./hypothesis/{}.json'.format(filename), 'w') as f:
                        json.dump(outputAll, f)
                    # print(json.dumps(outputAll))
                else:
                    sys.stderr.write("Error.\n")

    return sys.stderr.write("\nHypothesis generator has finished. {} QUERIES completed.\n".format(len(outputAll)))


if __name__ == '__main__':
    seed = list([
        'HGNC:17646',  # NGLY1 human gene
        'HGNC:633'  # AQP1 human gene
    ])
    #seed=['HGNC:17646', 'HGNC:633']
    #seed=['NGLY1', 'AQP1']
    #query(seed,'ngly1_aqp1_port7689',port='7689')
    # seed=['NCBIGene:55768', 'NCBIGene:358']
    #query(seed, 'ngly1_aqp1_port7688', port='7688')
    open_query(seed, queryname='ngly1_aqp1', port='7689')
