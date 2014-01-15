class environment:
      data = {
        "release": 1,
        "mode": "ha_compact"
      }
      interfaces = {
        'eth0': ["public", "floating"],
        'eth1': ["fixed"],
        'eth2': ["storage", "management"],
        'eth3': ["fuelweb_admin"]
      }
      special_roles = {}
      node_roles = [
        ['controller'],
        ['controller'],
        ['controller'],
        ['compute', 'cinder']
      ]
      net_tag = {
         'management': 730,
         'storage': 732,
         'fixed': None
      }
      deploy_timeout = 180 * 60
      settings = {
        "savanna": True,
        "murano": True,
        "ceilometer": True,
        "volumes_lvm": True,
        "libvirt_type": "kvm"
      }
      ostf_should_fail = 10
      ostf_timeout = 6 * 60 * 60
      ostf_test_sets = ['ha', 'smoke', 'sanity', 'platform_tests']
      net_cidr = {}
      net_ip_ranges = {}
      gateway = None
