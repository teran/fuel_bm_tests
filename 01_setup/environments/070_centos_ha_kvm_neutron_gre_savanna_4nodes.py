class environment:
      data = {
        "release": 1,
        "mode": "ha_compact"
      }
      interfaces = {
        'eth0': ["public"],
        'eth1': ["private"],
        'eth2': ["storage", "management"],
        'eth3': ["fuelweb_admin"]
      }
      special_roles = {}
      node_roles = [
        ['controller', 'cinder'],
        ['controller', 'cinder'],
        ['controller', 'cinder'],
        ['compute']
      ]
      net_tag = {
         'management': 730,
         'storage': 732,
         'fixed': None
      }
      deploy_timeout = 180 * 60
      settings = {
        "savanna": True,
        "volumes_lvm": True,
        "net_provider": 'neutron',
        "net_segment_type": 'gre',
        "libvirt_type": "kvm"
      }
      ostf_should_fail = 2
      ostf_timeout =  120 * 60
      ostf_test_sets = ['ha', 'smoke', 'sanity', 'platform_tests']
      net_cidr = {}
      net_ip_ranges = {}
      gateway = None
