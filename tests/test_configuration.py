import pychirp
import unittest


class TestConfiguration(unittest.TestCase):
    def test_empty_configuration(self):
        cfg = pychirp.Configuration(argv=None)
        self.assertEquals(pychirp.Path(), cfg.location)
        self.assertIsNone(cfg.connection_target)
        self.assertIsNone(cfg.connection_timeout)
        self.assertIsNone(cfg.connection_identification)

    def test_update(self):
        cfg = pychirp.Configuration(['test.py', 'config_a.json'])
        cfg.update('{"chirp": {"location": "/Home"}}')
        self.assertEqual(pychirp.Path("/Home"), cfg.location)
        self.assertRaises(pychirp.BadConfiguration, lambda: cfg.update('{'))

    def test_config_file(self):
        cfg = pychirp.Configuration(['test.py', 'config_a.json'])
        self.assertEqual(pychirp.Path('/Test'), cfg.location)
        self.assertEqual('localhost:12345', cfg.connection_target)
        self.assertAlmostEqual(1.234, cfg.connection_timeout)
        self.assertEqual('Hello World', cfg.connection_identification)

    def test_config_file_priority(self):
        cfg = pychirp.Configuration(['test.py', 'config_a.json', 'config_b.json'])
        self.assertEqual(pychirp.Path('/Pudding'), cfg.location)
        self.assertIsNone(cfg.connection_target)

    def test_command_line_override(self):
        cfg = pychirp.Configuration(['test.py', 'config_a.json', '--connection_target=my-host:1234',
                                     '--connection_timeout=0.555', '-i', 'Dude', '--location=/Home'])
        self.assertEqual(pychirp.Path('/Home'), cfg.location)
        self.assertEqual('my-host:1234', cfg.connection_target)
        self.assertAlmostEqual(0.555, cfg.connection_timeout)
        self.assertEqual('Dude', cfg.connection_identification)

    def test_json_overrides(self):
        cfg = pychirp.Configuration(['test.py', 'config_a.json', '--json={"my-age": 42}', '-j', '{"my-id": 55}',
                                     '--json={"chirp": {"location": "/Somewhere"}}', '--location=/Home'])
        self.assertEqual(42, cfg.config['my-age'])
        self.assertEqual(55, cfg.config['my-id'])
        self.assertEqual(pychirp.Path('/Home'), cfg.location)

    def test_bad_configuration_file(self):
        self.assertRaises(pychirp.BadConfiguration, lambda: pychirp.Configuration(['test.py', 'config_c.json']))

    def test_bad_command_line(self):
        self.assertRaises(pychirp.BadCommandLine, lambda: pychirp.Configuration(['test.py', '--hey-dude']))

    def test_str(self):
        cfg = pychirp.Configuration(['test.py', 'config_a.json'])
        self.assertRegex(str(cfg), r'.*localhost:12345.*')

if __name__ == '__main__':
    unittest.main()

