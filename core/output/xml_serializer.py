# -*- coding: utf-8 -*-
"""XML serializer with namespaces, CDATA, pretty-print, validation."""

import xml.etree.ElementTree as ET, os, re
from xml.dom import minidom
from typing import Any, Optional


class XmlConfig:
    def __init__(self, root_name: str = "root", encoding: str = "UTF-8",
                 pretty_print: bool = True,
                 namespaces: Optional[dict[str, str]] = None) -> None:
        self.root_name, self.encoding = root_name, encoding
        self.pretty_print, self.namespaces = pretty_print, namespaces or {}


class CDataWrapper:
    def __init__(self, text: str) -> None:
        if "]]>" in text:
            raise ValueError("CDATA value must not contain ']]>'")
        self.text = text

    def __str__(self) -> str:
        return f"<![CDATA[{self.text}]]>"


class XmlElement:
    """Fluent XML element builder with text, CDATA, and children."""

    def __init__(self, tag: str, attrib: Optional[dict[str, str]] = None) -> None:
        self._tag, self._attrib = tag, attrib or {}
        self._children: list["XmlElement"] = []
        self._text: Optional[str] = None
        self._cdata: Optional[CDataWrapper] = None

    def with_text(self, text: str) -> "XmlElement":
        self._text, self._cdata = text, None
        return self

    def with_cdata(self, text: str) -> "XmlElement":
        self._cdata, self._text = CDataWrapper(text), None
        return self

    def with_attrib(self, key: str, value: str) -> "XmlElement":
        self._attrib[key] = value
        return self

    def add_child(self, child: "XmlElement") -> "XmlElement":
        self._children.append(child)
        return self

    def _build(self, parent: ET.Element, ns: str = "") -> None:
        e = ET.SubElement(parent, f"{ns}{self._tag}" if ns else self._tag, attrib=self._attrib)
        if self._cdata:
            e.text = str(self._cdata)
        else:
            e.text = self._text
        for c in self._children:
            c._build(e, ns)


class XmlValidation:
    @staticmethod
    def is_well_formed(content: str) -> bool:
        try:
            ET.fromstring(content)
            return True
        except ET.ParseError:
            return False

    @staticmethod
    def validate_file(filepath: str) -> bool:
        try:
            ET.parse(filepath)
            return True
        except (ET.ParseError, OSError):
            return False


class XmlSerializer:
    """High-level XML serialiser with namespace and CDATA support."""

    def __init__(self, config: Optional[XmlConfig] = None) -> None:
        self.config = config or XmlConfig()

    def serialize(self, root_element: XmlElement, filepath: str) -> None:
        d = os.path.dirname(filepath)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        root_attrib: dict[str, str] = {}
        ns_prefix = ""
        for prefix, uri in self.config.namespaces.items():
            root_attrib[f"xmlns:{prefix}" if prefix else "xmlns"] = uri
            ns_prefix = f"{prefix}:"
        root = ET.Element(self.config.root_name, attrib=root_attrib)
        for child in root_element._children:
            child._build(root, ns_prefix)
        if root_element._cdata:
            root.text = str(root_element._cdata)
        else:
            root.text = root_element._text
        if self.config.pretty_print:
            raw = ET.tostring(root, encoding=self.config.encoding)
            dom = minidom.parseString(raw)
            with open(filepath, "wb") as fh:
                fh.write(dom.toprettyxml(indent="  ", encoding=self.config.encoding))
        else:
            decl = f'<?xml version="1.0" encoding="{self.config.encoding}"?>\n'
            with open(filepath, "wb") as fh:
                fh.write(decl.encode(self.config.encoding))
                fh.write(ET.tostring(root, encoding=self.config.encoding))

    def deserialize(self, filepath: str) -> ET.Element:
        try:
            return ET.parse(filepath).getroot()
        except (ET.ParseError, OSError) as exc:
            raise ValueError(f"XML parse error: {exc}") from exc

    @staticmethod
    def sanitize_tag(name: str) -> str:
        out = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(name))
        if not out or out[0].isdigit() or out[0] == "-":
            out = f"_{out}"
        return out
