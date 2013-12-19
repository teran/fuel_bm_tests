###################################
import sys
import os
import time
import logging
import re
import argparse
from fuelweb_test.models.nailgun_client import NailgunClient

###################################
def load_env(template):
  template
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
   fileHandler = logging.FileHandler(log_file, mode='w')
   fileHandler.setFormatter(formatter)
   l.setLevel(level)
   l.addHandler(fileHandler)

   if stdout:
     stdoutfomratter = logging.Formatter(stdoutformat)
     streamHandler = logging.StreamHandler(sys.stdout)
     streamHandler.setFormatter(stdoutfomratter)
     l.addHandler(streamHandler)

###################################
def ostf_run(log, client, cluster_id, test_sets=None, should_fail=0, timeout=10 * 60):

  test_sets = test_sets \
    if test_sets is not None \
    else ['smoke', 'sanity']

  try:
    client.ostf_run_tests(cluster_id, test_sets)
  except:
    return "ERROR - OSTF Server is not available"

  set_result_list = ostf_test_wait(client, cluster_id, timeout)
  passed = 0
  failed = 0
  logfile = log + '.ostf'
  setup_logger('ostflog', logfile, logging.INFO, '%(message)s', '%(message)s', False)
  ostflog = logging.getLogger('ostflog')
  ostflog.propagate = False

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
    """
    wait(predicate, interval=5, timeout=None) - wait until predicate will 
    become True. Returns number of seconds that is left or 0 if timeout is None.

    Options:

    interval - seconds between checks.

    timeout  - raise TimeoutError if predicate won't become True after 
    this amount of seconds. 'None' disables timeout.
    """
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
def remove_env(admin_node_ip, env_name, dosnapshot=False, keepalive=False):

  client = NailgunClient(admin_node_ip)
  cluster_id = client.get_cluster_id(env_name)
  need_to_wait_for_nodes = False
  all_nodes = []

  if cluster_id:
    if dosnapshot:
      task = client.generate_logs()
      result = task_wait(client, task, 120, 10)
    if keepalive:
      return "OK - Keep alive is enabled, keeping env alive"
    cluster_nodes = client.list_cluster_nodes(cluster_id)
    if len(cluster_nodes) > 0:
      need_to_wait_for_nodes = True
      all_nodes = client.list_nodes()
    client.delete_cluster(cluster_id)
  else:
    return "OK"

  for i in range(12):
    cluster_id = client.get_cluster_id(env_name)
    if cluster_id:
      time.sleep(5)

  if cluster_id:
    return "Can't delete cluster"

  for i in range(60):
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

  # old cluster is gone so we're ok to create a new cluster for tests
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

  # configure network
  network_list = client.get_networks(cluster_id)['networks']
  for network in network_list:
    if network["name"] in env.net_tag:
      network['vlan_start'] = env.net_tag[network["name"]]
  client.update_network(cluster_id, networks=network_list)

  if "net_provider" in env.settings:
    if env.settings["net_provider"] == 'neutron' and env.settings["net_segment_type"] == 'vlan' and 'neutron_vlan_range' in env.settings:
      network_conf = client.get_networks(cluster_id)
      network_conf['neutron_parameters']['L2']['phys_nets']['physnet2']['vlan_range'] = env.settings['neutron_vlan_range']
      client.update_network(cluster_id, networks=network_conf, all_set=True)

  # configure attributes
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
    if len(all_nodes) < len(env.node_roles):
      time.sleep(10)

  # check if we have anough nodes for our test case
  if len(all_nodes) < len(env.node_roles):
    return "Not enough nodes"

  nodes_data = []
  node_local_id = 0

  for node in all_nodes:
    if node_local_id < len(env.node_roles):
      #print "Found node id: {}".format(node['id'])
      node_data = {
        'cluster_id': cluster_id,
        'id': node['id'],
        'pending_addition': "true",
        'pending_roles': env.node_roles[node_local_id]
      }
      nodes_data.append(node_data)
      node_local_id += 1

  # add nodes to cluster
  client.update_nodes(nodes_data)
  cluster_nodes = client.list_cluster_nodes(cluster_id)
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
#  time.sleep(60)
#  return "OK"
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
def main():
      # Parse args
      parser = argparse.ArgumentParser(description='Deploy OpenStack and run tests.')
      parser.add_argument("fuel_node", type=str, help="Fuel admin node IP")
      parser.add_argument('environment', type=str, help='environment name we want to deploy and test')
      parser.add_argument("log", type=str, help="Log to store results in")
      parser.add_argument("-k", "--keep-env", help="Don't terminate OpenStack environment after deployment", action="store_true")
      parser.add_argument("-c", "--create-only", help="Create OpenStack environment and do not deploy it", action="store_true")

      args = parser.parse_args()
      admin_ip = args.fuel_node
      env = args.environment[:49]

      # args.keep_env = bool

      # Create mainlog
      setup_logger('mainlog', args.log, logging.INFO, '%(asctime)s : %(message)s', '%(message)s', True)
      mainlog = logging.getLogger('mainlog')
      mainlog.propagate = False

      # Removing env in case it exists
      remove_result = remove_env(admin_ip, env, False, False)
      if remove_result[:2] == "OK":
        mainlog.info('%s environment preliminary removal: %s', env, remove_result)
      else:
        mainlog.info('%s environment preliminary removal: ERROR - %s', env, remove_result)
      # Create env in our fuel
      setup_result = setup_env(admin_ip, env)
      if setup_result == "OK":
        mainlog.info('%s environment configuration: OK', env)
        if args.create_only:
          sys.exit(0)
        netverify_result = verify_network(admin_ip, env)
        # Env created and configured, let's verify network before we proceed
        if netverify_result == "OK":
          mainlog.info('%s environment pre-deployment network verification: OK', env)
  
          # Network is OK so we can deploy our env now
          deploy_result = deploy_cluster(admin_ip, env)
          #time.sleep(30)
          #deploy_result = "OK"
          if deploy_result == "OK":
            mainlog.info('%s environment deployment: OK', env) 
 
            # Env deployed, lets run network verification again
            netverify_result = verify_network(admin_ip, env)
            if netverify_result == "OK":
              mainlog.info('%s environment post-deployment network verification: OK', env)
            elif re.search('not implemented yet', netverify_result):
              mainlog.info('%s environment post-deployment network verification: OK - %s', env, netverify_result)
            else:
              mainlog.info('%s environment post-deployment network verification: ERROR - %s', env, netverify_result)
  
            # Run OSTF via fuel master node and report results
            ostf_result = run_ostf(admin_ip, env, args.log)
            if ostf_result[:2] == "OK":
              mainlog.info('%s environment OSTF result: %s', env,  str(ostf_result))
            else:
              mainlog.info('%s environment OSTF result: %s', env,  str(ostf_result))
 
            # We're done, let's remove our env now
            remove_result = remove_env(admin_ip, env, True, args.keep_env)
            if remove_result[:2] == "OK":
              mainlog.info('%s environment removal: %s', env, remove_result)
            else:
              mainlog.info('%s environment removal: ERROR - %s', env, remove_result)
  
          else:
            mainlog.info('%s environment deployment: ERROR - %s', env, deploy_result)

            remove_result = remove_env(admin_ip, env, True, args.keep_env)
            if remove_result[:2] == "OK":
              mainlog.info('%s environment removal: %s', env, remove_result)
            else:
              mainlog.info('%s environment removal: ERROR - %s', env, remove_result)
        else:
          mainlog.info('%s environment pre-deployment network verification: ERROR - %s', env, netverify_result)
          remove_result = remove_env(admin_ip, env, True, args.keep_env)
          if remove_result[:2] == "OK":
            mainlog.info('%s environment removal: %s', env, remove_result)
          else:
            mainlog.info('%s environment removal: ERROR - %s', env, remove_result)
      else:
        mainlog.info('%s environment configuration: ERROR - %s', env, setup_result)
  

###################################
if __name__ == '__main__':
  main()

