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
        "volumes_lvm": True,
        "murano": True,
        "net_provider": 'neutron',
        "net_segment_type": 'vlan',
        "neutron_vlan_range": [ 1000, 1009 ],
        "libvirt_type": "kvm"
      }
      ostf_should_fail = 10
      ostf_timeout = 6 * 60 * 60
      ostf_test_sets = ['ha', 'smoke', 'sanity', 'platform_tests']
