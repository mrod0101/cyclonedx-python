# encoding: utf-8

# This file is part of CycloneDX Python Lib
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) OWASP Foundation. All Rights Reserved.

import json
import sys
import xml.etree.ElementTree
from datetime import datetime, timezone
from unittest import TestCase
from uuid import uuid4
from xml.dom import minidom
from typing import Any

if sys.version_info >= (3, 8, 0):
    from importlib.metadata import version
else:
    from importlib_metadata import version

cyclonedx_bom_name: str = 'cyclonedx-bom'
cyclonedx_bom_version: str = version(cyclonedx_bom_name)
cyclonedx_lib_name: str = 'cyclonedx-python-lib'
cyclonedx_lib_version: str = version(cyclonedx_lib_name)
single_uuid: str = 'urn:uuid:{}'.format(uuid4())


class BaseJsonTestCase(TestCase):

    def assertEqualJson(self, a: str, b: str) -> None:
        self.assertEqual(
            json.dumps(json.loads(a), sort_keys=True),
            json.dumps(json.loads(b), sort_keys=True)
        )

    def assertEqualJsonBom(self, a: str, b: str) -> None:
        """
        Remove UUID before comparison as this will be unique to each generation
        """
        ab, bb = json.loads(a), json.loads(b)

        # Null serialNumbers
        ab['serialNumber'] = single_uuid
        bb['serialNumber'] = single_uuid

        # Unify timestamps to ensure they will compare
        now = datetime.now(tz=timezone.utc)
        ab['metadata']['timestamp'] = now.isoformat()
        bb['metadata']['timestamp'] = now.isoformat()

        # Align 'this' Tool Version
        if 'tools' in ab['metadata'].keys():
            for i, tool in enumerate(ab['metadata']['tools']):
                if tool['name'] == cyclonedx_lib_name:
                    ab['metadata']['tools'][i]['version'] = cyclonedx_lib_version
                elif tool['name'] == cyclonedx_bom_name:
                    ab['metadata']['tools'][i]['version'] = cyclonedx_bom_version

        if 'tools' in bb['metadata'].keys():
            for i, tool in enumerate(bb['metadata']['tools']):
                if tool['name'] == cyclonedx_lib_name:
                    bb['metadata']['tools'][i]['version'] = cyclonedx_lib_version
                elif tool['name'] == cyclonedx_bom_name:
                    bb['metadata']['tools'][i]['version'] = cyclonedx_bom_version

        self.assertEqualJson(json.dumps(ab), json.dumps(bb))


class BaseXmlTestCase(TestCase):

    def assertEqualXml(self, a: str, b: str) -> None:
        da, db = minidom.parseString(a), minidom.parseString(b)
        self.assertTrue(self._is_equal_xml_element(da.documentElement, db.documentElement),
                        'XML Documents are not equal: \n{}\n{}'.format(da.toxml(), db.toxml()))

    def assertEqualXmlBom(self, a: str, b: str, namespace: str) -> None:
        """
        Sanitise some fields such as timestamps which cannot have their values directly compared for equality.
        """
        ba, bb = xml.etree.ElementTree.fromstring(a), xml.etree.ElementTree.fromstring(b)

        # Align serialNumbers
        ba.set('serialNumber', single_uuid)
        bb.set('serialNumber', single_uuid)

        # Align timestamps in metadata
        now = datetime.now(tz=timezone.utc)
        metadata_ts_a = ba.find('./{{{}}}metadata/{{{}}}timestamp'.format(namespace, namespace))
        if metadata_ts_a is not None:
            metadata_ts_a.text = now.isoformat()

        metadata_ts_b = bb.find('./{{{}}}metadata/{{{}}}timestamp'.format(namespace, namespace))
        if metadata_ts_b is not None:
            metadata_ts_b.text = now.isoformat()

        # Align 'this' Tool Version
        lib_tool = ba.find('.//*/{{{}}}tool[{{{}}}name="cyclonedx-python-lib"]'.format(namespace, namespace))
        if lib_tool:
            lib_tool.find('./{{{}}}version'.format(namespace)).text = cyclonedx_lib_version
        lib_tool = bb.find('.//*/{{{}}}tool[{{{}}}name="cyclonedx-python-lib"]'.format(namespace, namespace))
        if lib_tool:
            lib_tool.find('./{{{}}}version'.format(namespace)).text = cyclonedx_lib_version
        this_tool = ba.find('.//*/{{{}}}tool[{{{}}}name="cyclonedx-bom"]'.format(namespace, namespace))
        if this_tool:
            this_tool.find('./{{{}}}version'.format(namespace)).text = cyclonedx_bom_version
        this_tool = bb.find('.//*/{{{}}}tool[{{{}}}name="cyclonedx-bom"]'.format(namespace, namespace))
        if this_tool:
            this_tool.find('./{{{}}}version'.format(namespace)).text = cyclonedx_bom_version

        self.assertEqualXml(
            xml.etree.ElementTree.tostring(ba, 'unicode'),
            xml.etree.ElementTree.tostring(bb, 'unicode')
        )

    def _is_equal_xml_element(self, a: Any, b: Any) -> bool:
        if a.tagName != b.tagName:
            return False
        if sorted(a.attributes.items()) != sorted(b.attributes.items()):
            return False

        """
        Remove any pure whitespace Dom Text Nodes before we compare

        See: https://xml-sig.python.narkive.com/8o0UIicu
        """
        for n in a.childNodes:
            if n.nodeType == n.TEXT_NODE and n.data.strip() == '':
                a.removeChild(n)
        for n in b.childNodes:
            if n.nodeType == n.TEXT_NODE and n.data.strip() == '':
                b.removeChild(n)

        if len(a.childNodes) != len(b.childNodes):
            return False
        for ac, bc in zip(a.childNodes, b.childNodes):
            if ac.nodeType != bc.nodeType:
                return False
            if ac.nodeType == ac.TEXT_NODE and ac.data != bc.data:
                return False
            if ac.nodeType == ac.ELEMENT_NODE and not self._is_equal_xml_element(ac, bc):
                return False
        return True
