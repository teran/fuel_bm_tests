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
        "volumes_lvm": True,
        "libvirt_type": "kvm"
      }
      ostf_should_fail = 0
      ostf_timeout = 30 * 60
      ostf_test_sets = ['ha', 'smoke', 'sanity', 'platform_tests']
