###################################
import sys
import os
import time
import logging
import re
import argparse
from ipaddr import IPNetwork
from fuelweb_test.models.nailgun_client import NailgunClient

###################################
def load_env(template):

  loaded = getattr(__import__(template), "environment")
  loaded.data['name'] = template
  return loaded

###################################
class DevopsError(Exception):
  message = "Devops Error"
class TimeoutError(DevopsError):
  pass

###################################
def ostf_test_wait(client, cluster_id, timeout):
  wait(
    lambda: all([run['status'] == 'finished'
                 for run in
                 client.get_ostf_test_run(cluster_id)]),
    timeout=timeout)
  return client.get_ostf_test_run(cluster_id)

###################################
def setup_logger(logger_name, log_file, level=logging.INFO, logformat='%(asctime)s : %(message)s', stdoutformat='%(message)s', stdout=False):
  l = logging.getLogger(logger_name)
  formatter = logging.Formatter(logformat)
  fileHandler = logging.FileHandler(log_file, mode='a')
  fileHandler.setFormatter(formatter)
  l.setLevel(level)
  l.addHandler(fileHandler)

  if stdout:
    stdoutfomratter = logging.Formatter(stdoutformat)
    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setFormatter(stdoutfomratter)
    l.addHandler(streamHandler)
###################################
def get_range(ip_network, ip_range=0):
  net = list(IPNetwork(ip_network))
  half = len(net)/2
  if ip_range == 0:
    return [[str(net[2]), str(net[-2])]]
  elif ip_range == 1:
    return [[str(net[half]), str(net[-2])]]
  elif ip_range == -1:
    return [[str(net[2]), str(net[half - 1])]]
  elif ip_range == 2:
    # for neutron vlan
    return [str(net[half]), str(net[-2])]

###################################
def ostf_run(log, client, cluster_id, test_sets=None, should_fail=0, timeout=10 * 60):

  # define default test_sets if not provided by the environment
  test_sets = test_sets \
    if test_sets is not None \
    else ['smoke', 'sanity']

  # run ostf
  try:
    client.ostf_run_tests(cluster_id, test_sets)
  except:
    return "ERROR - OSTF Server is not available"

  # wait for ostf results
  set_result_list = ostf_test_wait(client, cluster_id, timeout)
  passed = 0
  failed = 0
  logfile = log + '.ostf'
  setup_logger('ostflog', logfile, logging.INFO, '%(message)s', '%(message)s', False)
  ostflog = logging.getLogger('ostflog')
  ostflog.propagate = False

  # analyze ostf results and write details to ostf log
  for set_result in set_result_list:
    for testik in  set_result['tests']:
      ostflog.info('[%s] %s: %s', testik['testset'], testik['name'], testik['status'])

      if testik['status'] != 'success' and testik['message'] != "":
        ostflog.info('\t%s', testik['message'])

    passed += len(
                filter(
                    lambda test: test['status'] == 'success',
                     set_result['tests']
                )
    )
    failed += len(
                filter(
                    lambda test: test['status'] == 'failure' or
                    test['status'] == 'error',
                    set_result['tests']
                )
    )

  # prepare result
  if failed <= should_fail:
    result = "OK\n"
    result += "\tPassed tests: %s\n" % passed
    result += "\tFailed tests: %s, should fail: %s" % (failed, should_fail)
  else:
    result = "ERROR\n"
    result += "\tPassed tests: %s\n" % passed
    result += "\tFailed tests: %s, should fail: %s" % (failed, should_fail)

  return result

###################################
def wait(predicate, interval=5, timeout=None):

  start_time = time.time()
  while not predicate():
    if timeout and start_time + timeout < time.time():
      raise TimeoutError("Waiting timed out")

    seconds_to_sleep = interval
    if timeout:
      seconds_to_sleep = max(
          0,
          min(seconds_to_sleep, start_time + timeout - time.time()))
    time.sleep(seconds_to_sleep)

  return timeout + start_time - time.time() if timeout else 0

###################################
def make_snapshot (admin_node_ip):

  client = NailgunClient(admin_node_ip)
  task = client.generate_logs()
  result = task_wait(client, task, 600, 10)

  if result['status'] == 'ready':
    return "OK"
  else:
    return result['message']

###################################
def remove_env(admin_node_ip, env_name):

  client = NailgunClient(admin_node_ip)
  cluster_id = client.get_cluster_id(env_name)
  need_to_wait_for_nodes = False
  all_nodes = []

  if cluster_id:
    cluster_nodes = client.list_cluster_nodes(cluster_id)
    if len(cluster_nodes) > 0:
      need_to_wait_for_nodes = True
      all_nodes = client.list_nodes()
    client.delete_cluster(cluster_id)
  else:
    return "OK"

  # wait for cluster to disappear
  for i in range(60):
    cluster_id = client.get_cluster_id(env_name)
    if cluster_id:
      time.sleep(10)

  # fail if cluster is still around
  if cluster_id:
    return "Can't delete cluster"

  # wait for removed nodes to come back online
  for i in range(90):
    cur_nodes = client.list_nodes()
    if len(cur_nodes) < len(all_nodes):
      time.sleep(10)

  if len(cur_nodes) < len(all_nodes):
    return "Timeout while waiting for removed nodes ({}) to come back up".format(len(cluster_nodes))

  return "OK"

###################################
def setup_env(admin_node_ip, env_name):

  client = NailgunClient(admin_node_ip)
  cluster_id = client.get_cluster_id(env_name)
  release_id = client.get_release_id()

  # delete previous cluster with the same name
  if cluster_id:
    client.delete_cluster(cluster_id)

  for i in range(6):
    cluster_id = client.get_cluster_id(env_name)
    if cluster_id:
      time.sleep(5)

  if cluster_id:
    return "Can't delete cluster"

  # old cluster is gone so we're ok to create a new cluster
  env = load_env(env_name)
  data = env.data

  if "net_provider" in env.settings:
    data.update(
      {  
        'net_provider': env.settings["net_provider"],
        'net_segment_type': env.settings["net_segment_type"]
      }
    )

  client.create_cluster(data=data)
  time.sleep(5)
  cluster_id = client.get_cluster_id(env_name)

  # configure networks
  network_conf = client.get_networks(cluster_id)
  network_list = network_conf['networks']

  for network in network_list:
    # set vlan tags
    if network["name"] in env.net_tag:
      network['vlan_start'] = env.net_tag[network["name"]]
    # set CIDR and related net stuff
    if network["name"] in env.net_cidr:
      network['cidr'] = env.net_cidr[network["name"]]
      if network["name"] == "public":
        if env.gateway:
          network["gateway"] = env.gateway
        else:
          network["gateway"] = str(list(IPNetwork(network['cidr']))[1])
      if network["name"] in env.net_ip_ranges:
        network['ip_ranges'] = env.net_ip_ranges[network["name"]]
      else:
        if network["name"] == "public":
          network['ip_ranges'] = get_range(network['cidr'], -1)
        elif network["name"] == "floating":
          network['ip_ranges'] = get_range(network['cidr'], 1)
        else:
          network['ip_ranges'] = get_range(network['cidr'], 0)
      network['netmask'] = str(IPNetwork(network['cidr']).netmask)
      network['network_size'] = len(list(IPNetwork((network['cidr']))))

  network_conf['networks'] = network_list

  # update neutron settings
  if "net_provider" in env.settings:
    if env.settings["net_provider"] == 'neutron':
      # check if we need to set vlan tags
      if env.settings["net_segment_type"] == 'vlan' and 'neutron_vlan_range' in env.settings:
        network_conf['neutron_parameters']['L2']['phys_nets']['physnet2']['vlan_range'] = env.settings['neutron_vlan_range']
      # check and update networks CIDR/netmask/size/etc
      if 'net04' in env.net_cidr:
        network_conf['neutron_parameters']['predefined_networks']['net04']['L3']['cidr'] = env.net_cidr['net04']
        network_conf['neutron_parameters']['predefined_networks']['net04']['L3']['gateway'] = str(list(IPNetwork(env.net_cidr['net04']))[1])
      if 'public' in env.net_cidr:
        network_conf['neutron_parameters']['predefined_networks']['net04_ext']['L3']['cidr'] = env.net_cidr['public']
        if env.gateway:
          network_conf['neutron_parameters']['predefined_networks']['net04_ext']['L3']['gateway'] = env.gateway
        else:
          network_conf['neutron_parameters']['predefined_networks']['net04_ext']['L3']['gateway'] = str(list(IPNetwork(env.net_cidr['public']))[1])
        if 'net04_ext' in env.net_ip_ranges:
          network_conf['neutron_parameters']['predefined_networks']['net04_ext']['L3']['floating'] = env.net_ip_ranges["net04_ext"]
        else:
          network_conf['neutron_parameters']['predefined_networks']['net04_ext']['L3']['floating'] = get_range(env.net_cidr['public'], 2)

  # push updated network to Fuel API
  client.update_network(cluster_id, networks=network_conf, all_set=True)

  # configure cluster attributes
  attributes = client.get_cluster_attributes(cluster_id)

  for option in env.settings:
    section = False
    if option in ('savanna', 'murano', 'ceilometer'):
      section = 'additional_components'
    if option in ('volumes_ceph', 'images_ceph', 'volumes_lvm'):
      section = 'storage'
    if option in ('libvirt_type', 'vlan_splinters'):
      section = 'common'
    if section:
      attributes['editable'][section][option]['value'] = env.settings[option]

  attributes['editable']['common']['debug']['value'] = True
  client.update_cluster_attributes(cluster_id, attributes)

  # get all nodes
  for i in range(18):
    all_nodes = client.list_nodes()
    if len(all_nodes) < len(env.node_roles) + len(env.special_roles):
      time.sleep(10)

  # check if we have enough nodes for our test case
  if len(all_nodes) < len(env.node_roles) + len(env.special_roles):
    return "Not enough nodes"

  nodes_data = []
  node_local_id = 0

  # go through unassigned nodes and update their pending_roles according to environment settings
  for node in all_nodes:
    if node['cluster'] == None and (node_local_id < len(env.node_roles) or node['mac'] in env.special_roles):
      if node['mac'] in env.special_roles:
        node_role = env.special_roles[node['mac']]
      else:
        node_role = env.node_roles[node_local_id]
        node_local_id += 1
      node_data = {
        'cluster_id': cluster_id,
        'id': node['id'],
        'pending_addition': "true",
        'pending_roles': node_role
      }
      nodes_data.append(node_data)

  # add nodes to cluster
  client.update_nodes(nodes_data)

  # check if we assigned all nodes we wanted to
  cluster_nodes = client.list_cluster_nodes(cluster_id)
  if len(cluster_nodes) != len(env.node_roles) + len(env.special_roles):
    return "Not enough nodes"

  # move networks to appropriate nodes interfaces (according to environment settings)
  for node in cluster_nodes:
    node_id = node['id']
    interfaces_dict = env.interfaces
    interfaces = client.get_node_interfaces(node_id)
    for interface in interfaces:
      interface_name = interface['name']
      interface['assigned_networks'] = []
      for allowed_network in interface['allowed_networks']:
        key_exists = interface_name in interfaces_dict
        if key_exists and \
        allowed_network['name'] \
        in interfaces_dict[interface_name]:
          interface['assigned_networks'].append(allowed_network)

    client.put_node_interfaces(
      [{'id': node_id, 'interfaces': interfaces}])
  return "OK"

###################################
def task_wait(client, task, timeout, interval=5):
  try:
    wait(
      lambda: client.get_task(
        task['id'])['status'] != 'running',
        interval=interval,
        timeout=timeout
    )
  except TimeoutError:
    raise TimeoutError(
      "Waiting task \"{task}\" timeout {timeout} sec "
      "was exceeded: ".format(task=task["name"], timeout=timeout))

  return client.get_task(task['id'])

###################################
def verify_network(admin_node_ip, env_name):
  client = NailgunClient(admin_node_ip)
  cluster_id = client.get_cluster_id(env_name)
  env = load_env(env_name)

  task = client.verify_networks(cluster_id, client.get_networks(cluster_id)['networks'])
  result = task_wait(client, task, 300, 10)
  if result['status'] == 'ready':
    return "OK"
  else:
    return result['message']

###################################
def run_ostf(admin_node_ip, env_name, log):
  client = NailgunClient(admin_node_ip)
  cluster_id = client.get_cluster_id(env_name)
  env = load_env(env_name)

  result = ostf_run(log, client, cluster_id, env.ostf_test_sets, env.ostf_should_fail, env.ostf_timeout)
  return result

###################################
def deploy_cluster(admin_node_ip, env_name):
  client = NailgunClient(admin_node_ip)
  cluster_id = client.get_cluster_id(env_name)
  env = load_env(env_name)

  task = client.deploy_cluster_changes(cluster_id)
  result = task_wait(client, task, env.deploy_timeout, 30)
  if result['status'] == 'ready':
    return "OK"
  else:
    return result['message']

###################################
def run_action (name, admin_ip, env, mainlog, log):

  ###########
  if name == "create":
    setup_result = setup_env(admin_ip, env)

    if setup_result == "OK":
      mainlog.info('%s environment configuration: OK', env)
      return True
    else:
      mainlog.info('%s environment configuration: ERROR - %s', env, setup_result)
      return False

  ###########
  if name == "remove":

    remove_result = remove_env(admin_ip, env)

    if remove_result[:2] == "OK":
      mainlog.info('%s environment removal: %s', env, remove_result)
      return True
    else:
      mainlog.info('%s environment removal: ERROR - %s', env, remove_result)
      return False

  ###########
  if name == "netverify":

    netverify_result = verify_network(admin_ip, env)

    if netverify_result == "OK":
      mainlog.info('%s environment network verification: OK', env)
      return True
    elif re.search('not implemented yet', netverify_result):
      mainlog.info('%s environment network verification: OK - %s', env, netverify_result)
      return True
    else:
      mainlog.info('%s environment network verification: ERROR - %s', env, netverify_result)
      return False

  ###########
  if name == "deploy":

    deploy_result = deploy_cluster(admin_ip, env)

    if deploy_result == "OK":
      mainlog.info('%s environment deployment: OK', env)
      return True
    else:
      mainlog.info('%s environment deployment: ERROR - %s', env, deploy_result)
      return False

  ###########
  if name == "ostf":

    ostf_result = run_ostf(admin_ip, env, log)

    if ostf_result[:2] == "OK":
      mainlog.info('%s environment OSTF result: %s', env,  str(ostf_result))
      return True
    else:
      mainlog.info('%s environment OSTF result: %s', env,  str(ostf_result))
      return False

  ###########
  if name == "snapshot":
    snapshot_result = make_snapshot(admin_ip)
    if snapshot_result[:2] == "OK":
      mainlog.info('%s environment create diagnostic snapshot result: %s', env,  str(snapshot_result))
      return True
    else:
      mainlog.info('%s environment create diagnostic snapshot result: %s', env,  str(snapshot_result))
      return False


###################################
def main():
  # Parse args
  supported_actions = [ "create", "remove", "netverify", "deploy", "ostf", "snapshot"]
  parser = argparse.ArgumentParser(description='Deploy OpenStack and run Fuel health check.')
  parser.add_argument("fuel_node", type=str, help="Fuel admin node IP")
  parser.add_argument('environment', type=str, help='Environment name we want to deploy and test')
  parser.add_argument('action', type=str, help="Action we want to execute. Possible actions: {}".format(supported_actions))
  parser.add_argument("log", type=str, help="Logfile to store results in")
  parser.add_argument("-i", "--ignore-errors", help="Exit with 0 exit-code despite the errors we'v got", action="store_true")

  args = parser.parse_args()

  admin_ip = args.fuel_node
  env = args.environment[:49]

  # Create mainlog
  setup_logger('mainlog', args.log, logging.INFO, '%(asctime)s : %(message)s', '%(message)s', True)
  mainlog = logging.getLogger('mainlog')
  mainlog.propagate = False

  # Run some action
  if args.action in supported_actions:
    if run_action(args.action, admin_ip, env, mainlog, args.log):
      sys.exit(0)
    elif args.ignore_errors:
      sys.exit(0)
    else:
      sys.exit(1)


###################################
if __name__ == '__main__':
  main()
