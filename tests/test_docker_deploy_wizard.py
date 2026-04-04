# -*- coding: utf-8 -*-
import unittest

from ugreen_app.docker_deploy_wizard import analyze_docker_text, apply_docker_vars, list_bind_host_paths


class TestDockerDeployWizard(unittest.TestCase):
    def test_placeholder_replace(self):
        text = "docker run -e X=${DATA_DIR} -v ${DATA_DIR}:/data img"
        vars_list, _ = analyze_docker_text(text)
        kinds = {v.kind for v in vars_list}
        self.assertIn("placeholder", kinds)
        ids = {v.name for v in vars_list if v.kind == "placeholder"}
        self.assertIn("DATA_DIR", ids)
        by_id = {v.id: v for v in vars_list}
        p = next(v for v in vars_list if v.name == "DATA_DIR")
        out = apply_docker_vars(text, vars_list, {p.id: "/volume1/app"})
        self.assertIn("/volume1/app:/data", out)
        self.assertNotIn("${DATA_DIR}", out)

    def test_compose_volume(self):
        yml = """
services:
  web:
    image: nginx
    volumes:
      - /volume1/old:/usr/share/nginx/html:ro
"""
        vars_list, is_c = analyze_docker_text(yml)
        self.assertTrue(is_c)
        vols = [v for v in vars_list if v.kind == "volume"]
        self.assertTrue(vols)
        out = apply_docker_vars(yml, vars_list, {vols[0].id: "/volume1/new"})
        self.assertIn("/volume1/new:/usr/share/nginx/html:ro", out)
        self.assertNotIn("/volume1/old:", out)

    def test_port_host(self):
        text = "docker run -p 8080:80 -p 127.0.0.1:9000:9000 img"
        vars_list, _ = analyze_docker_text(text)
        ports = [v for v in vars_list if v.kind == "port"]
        self.assertGreaterEqual(len(ports), 1)
        by_full = {v.port_full: v for v in ports}
        v1 = by_full.get("8080:80")
        self.assertIsNotNone(v1)
        out = apply_docker_vars(text, vars_list, {v1.id: "18080"})
        self.assertIn("18080:80", out)
        v2 = by_full.get("127.0.0.1:9000:9000")
        if v2:
            out2 = apply_docker_vars(text, vars_list, {v1.id: "8080", v2.id: "19000"})
            self.assertIn("127.0.0.1:19000:9000", out2)

    def test_list_bind_host_paths(self):
        t = "services:\n  x:\n    volumes:\n      - /vol/a:/m\n"
        self.assertIn("/vol/a", list_bind_host_paths(t))


if __name__ == "__main__":
    unittest.main()
