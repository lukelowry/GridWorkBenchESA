# PW AuX: The functions for reading, writing, and interpreting PowerWorld auxiliary files
#
# Adam Birchfield, Texas A&M University
# 
# Log:
# 5/25/2022 Initial version
# 8/10/2022 Now can export AUX case files   
#

# Stages to implement: read, parse, form, write

import re
from ..utils.exceptions import AuxParseException, GridObjDNE
from ..utils import *
from ..analysis.contingencies import ContingencyAction, Contingency, ContingencySet


def Q(no_quotes):
    return "\"" + no_quotes + "\""

def NQ(with_quotes):
    return with_quotes[1:-1]

class PWAuxScriptBlock:

    def __init__(self, name):
        self.name = name
        self.statements = []

    def write(self, f):
        f.write("SCRIPT " + self.name + "\n{\n")
        for statement in self.statements:
            f.write(statement + "\n")
        f.write("}\n")

class PWAuxDataBlock:

    def __init__(self, object_type, field_names):
        self.object_type = object_type
        self.field_names = list(field_names)
        self.field_map = {field_names[i]:i for i in range(len(field_names))}
        self.data = []
        self.subdata_headers = []
        self.subdata_data = []

    def add_data_line(self, data_line=None):
        nf = len(self.field_names)
        if data_line is None:
            self.data.append(["" for i in range(nf)])
        else:
            self.data.append(data_line)
        self.subdata_headers.append([])
        self.subdata_data.append([])

    def set_value(self, index, field, value):
        self.data[index][self.field_map[field]] = str(value)

    def set_string(self, index, field, value):
        self.data[index][self.field_map[field]] = Q(value)

    def add_subdata(self, index, subdatatype, subdatadata):
        self.subdata_headers[index].append(subdatatype)
        self.subdata_data[index].append(subdatadata)
    
    def write(self, f):

        nf = len(self.field_names)
        
        # Write header with wraparound greater than specified length
        header_line_max_len = 100
        f.write("DATA (" + self.object_type + ", [")
        len_line = 9 + len(self.object_type)
        for i in range(nf):
            if len_line + len(self.field_names[i]) + 2 > header_line_max_len:
                f.write("\n    ")
                len_line = 4
            len_line += len(self.field_names[i]) + 2
            f.write(self.field_names[i])
            if i < nf-1:
                f.write(", ")
        f.write("])\n{\n")

        # Determine width per field
        field_max_width = 40
        field_len = [0 for _ in range(nf)]
        for i in range(len(self.data)):
            for j in range(len(self.data[i])):
                field_len[j] = min(max(field_len[j], len(f"{self.data[i][j]}")), 
                    field_max_width)

        # Write data and subdata
        for i in range(len(self.data)):
            for j in range(nf):
                f.write(f"{self.data[i][j]:{field_len[j]}}")
                if j < nf-1:
                    f.write(" ")
            f.write("\n")
            for j in range(len(self.subdata_headers[i])):
                f.write("<SUBDATA " + self.subdata_headers[i][j] + ">\n")
                for k in range(len(self.subdata_data[i][j])):
                    f.write(self.subdata_data[i][j][k]+"\n")
                f.write("</SUBDATA>\n");
        f.write("}\n\n")

class PWAuxFormat:

    def __init__(self, fname=None):
        self.reprog = re.compile(r'(?:^|(?<=\s))"?((?<!")[^\s"]+(?!")|(?<=")(?:[^"]|"")*(?="))"?(?:$|(?=\s))')
        self.concise = False
        self.script_blocks = []
        self.data_blocks = []
        if fname is not None:
            self.read_file(fname)

    def read_file(self, fname):
        self.concise = False
        self.script_blocks = []
        self.data_blocks = []
        self.parse_scope = 0 # 0 document, 1 script header, 2 script body, 
            # 3 data header, 4 data body, 5 subdata block
        self.in_multiline_comment = False
        self.line_carryover = []
        with open(fname) as f:
            for line_count, line in enumerate(f):
                line = self.parse_comments(line_count, line)
                if len(line) == 0:
                    continue
                self.parse_document_line(line_count, line)

    def parse_document_line(self, line_count, line):
        if self.parse_scope == 0: # Document
            if line[:6].lower() == "script":
                self.parse_scope = 1
            elif line[:4].lower() == "data":
                self.parse_scope = 3
            else:
                self.parse_scope = 3
                self.concise = True
            self.line_carryover = [line]
        elif self.parse_scope == 1: # SCRIPT header 
            if line == "{":
                self.parse_scope = 2
                full_header = "".join(self.line_carryover)
                self.script_blocks.append(PWAuxScriptBlock(full_header))
            else:
                self.line_carryover.append(line)
        elif self.parse_scope == 2: # SCRIPT body
            if line == "}":
                self.parse_scope = 0
            else:
                self.script_blocks[-1].statements.append(line)
        elif self.parse_scope == 3: # DATA header
            if line == "{":
                self.parse_scope = 4
                header = re.split("\(|\)", " ".join(self.line_carryover))
                if len(header) < 2:
                    raise AuxParseException(f"Header missing ( at line " + 
                        f"{line_count+1}")
                if header[0].strip() == "DATA":
                    header = re.split("\[|\]", header[1])
                    obj_type = header[0].split(",")[0].strip()
                else:
                    obj_type = header[0].strip()
                fields = [f.strip() for f in header[1].split(",")]
                self.data_blocks.append(PWAuxDataBlock(obj_type, fields))
            else:
                self.line_carryover.append(line)
        elif self.parse_scope == 4: # DATA body
            if line == "}":
                self.parse_scope = 0
            elif line[:8].lower() == "<subdata":
                self.parse_scope = 5
                self.line_carryover = [line[8:-1].strip()]
            else:
                try:
                    data_line = self.reprog.findall(line)
                    #data_line = self.parse_data_line(line)
                    self.data_blocks[-1].add_data_line(data_line)
                except Exception as e:
                    raise AuxParseException(str(e) + " while parsing file at line "
                        + str(line_count+1))
        elif self.parse_scope == 5: # SUBDATA
            if line == "</SUBDATA>":
                self.parse_scope = 4
                db = self.data_blocks[-1]
                i = len(db.subdata_headers) - 1 
                db.add_subdata(i, self.line_carryover[0], self.line_carryover[1:])
            else:
                self.line_carryover.append(line)

    def parse_comments(self, line_count, line):
        # Later replace with regex
        if "*/" not in line and "//" not in line and "/*" not in line: 
            return line.strip()
        line_chunks = []
        lasti = 0
        for i in range(len(line)):
            if i == len(line)-1:
                if not self.in_multiline_comment:
                    line_chunks.append(line[lasti:])
                break
            token = line[i:i+2]
            if self.in_multiline_comment:
                if token == "*/":
                    lasti = i + 2
                    self.in_multiline_comment = False
            elif token == "/*":
                self.in_multiline_comment = True
                line_chunks.append(line[lasti:i])
            elif token == "//":
                line_chunks.append(line[lasti:i])
                break
        line = "".join(line_chunks).strip()
        if len(line) > 1 and ("{" in line or "}" in line):
            raise AuxParseException(
                f"{{ or }} should be alone on line, line {line_count+1}")
        return line

    def write_file(self, fname):
        with open(fname, "w") as f:
            f.write(f"// AUX file written by GridWorkbench\n\n")
            for sb in self.script_blocks:
                sb.write(f)
            for db in self.data_blocks:
                db.write(f)

def make_db(wb, gwb_obj_name, pw_obj_name, obj_gen):
    fields = []
    for f, instr in wb.pw_instructions.items():
        otype, fname = f.split(".")
        if otype != gwb_obj_name:
            continue
        if "pwfield" not in instr or len(instr["pwfield"]) == 0:
            continue
        fields.append((fname, instr))
    db = PWAuxDataBlock(pw_obj_name, [f[1]["pwfield"][0] for f in fields])
    for i, obj in enumerate(obj_gen):
        db.add_data_line()
        for fname, instr in fields:
            pw_fname = instr["pwfield"][0]
            if hasattr(obj, fname):
                value = getattr(obj, fname)
            else:
                value = ""
            if "export_from_aux" not in instr:
                pass
            elif instr["export_from_aux"] == "default":
                pass
            elif instr["export_from_aux"][0] == ".":
                value = getattr(value, instr["export_from_aux"][1:])
            elif instr["export_from_aux"] == "connected":
                value = "Connected" if value else "Disconnected"
            elif instr["export_from_aux"] == "closed":
                value = "Closed" if value else "Open"
            elif instr["export_from_aux"] == "yesno":
                value = "Yes" if value else "No"
            else:
                raise AuxParseException("Unrecognized export instructions")
            if isinstance(value, str):
                db.set_string(i, pw_fname, value)
            else:
                db.set_value(i, pw_fname, value)
    return db

def export_aux(wb, fname):
    aux = PWAuxFormat()
    for branch in wb.branches:
        branch.pw_line_type = "Line" if branch.from_bus.nominal_kv == branch.to_bus.nominal_kv else "Transformer"
    aux.data_blocks = [
        make_db(wb, "region", "SuperArea", wb.regions),
        make_db(wb, "area", "Area", wb.areas),
        make_db(wb, "sub", "Substation", wb.subs),
        make_db(wb, "bus", "Bus", wb.buses),
        make_db(wb, "gen", "Gen", wb.gens),
        make_db(wb, "load", "Load", wb.loads),
        make_db(wb, "shunt", "Shunt", wb.shunts),
        make_db(wb, "branch", "Branch", wb.branches)
    ]
    aux.write_file(fname)

def import_aux(wb, fname, hush=False):
    regex_prog = re.compile(r'(?:^|(?<=\s))"?((?<!")[^\s"]+(?!")|(?<=")(?:[^"]|"")*(?="))"?(?:$|(?=\s))')

    aux = PWAuxFormat(fname)

    # Map from what powerworld calls the object type to GWB types
    otypes = {
        "superarea":"region", "area":"area", "substation":"sub", 
        "bus":"bus", "load":"load", "gen":"gen", "shunt":"shunt", "branch":"branch",
        "transformer":"branch"}

    for db in aux.data_blocks:

        # See if we know what to do with this type of object
        oname = db.object_type.lower()
        try:
            otype = otypes[oname]
        except KeyError:
            if not hush:
                print(f"Warning: {oname} not recognized Aux Block Type")
            continue

        # See the default_pw_instructions.py file
        # Basically check for which fields we know what to do with
        field_info = [None for _ in range(len(db.field_names))]
        for key, instr in wb.pw_instructions.items():
            obj_id, field_name = key.split(".")
            if obj_id != otype or "pwfield" not in instr:
                continue
            for pwfield in instr["pwfield"]:
                if pwfield in db.field_map:
                    field_info[db.field_map[pwfield]] = (field_name, instr)

        for data_line in db.data:

            # Start by going through all the fields for this object, doing
            # initial processing and putting it into a dictionary
            processed_obj_data = {}
            for x, finstr in zip(data_line, field_info):
                if finstr is None:
                    continue
                field_name, instr = finstr
                process_instr = instr["import_from_aux"] \
                    if "import_from_aux" in instr else "default"
                if process_instr == "default":
                    processed_obj_data[field_name] = x
                elif process_instr == "string":
                    processed_obj_data[field_name] = x #NQ(x)
                elif process_instr == "string_main":
                    processed_obj_data[otype] = x #NQ(x)
                elif process_instr == "int":
                    if x == '':#'""':
                        x = 0
                    processed_obj_data[field_name] = int(x)
                elif process_instr == "int_main":
                    if x == '':#'""':
                        x = 0
                    processed_obj_data[otype] = int(x)
                elif process_instr == "float":
                    if x == '':#'""':
                        x = 0
                    processed_obj_data[field_name] = float(x)
                elif process_instr in ["bool", "connected", "yesno", "closed"]:
                    x = x.lower()
                    if len(x) == 0:
                        x = False
                    elif x[0] == '"':
                        x = NQ(x)
                    if x in ['connected', 'yes', 'closed', 'true', '1']:
                        x = True
                    else:
                        x = False
                    processed_obj_data[field_name] = bool(x)
                elif process_instr == "skip":
                    continue
                else:
                    raise AuxParseException(
                        f"Unrecognized aux parse instructions {process_instr}")

            # Complicated process to make sure correct objects are identified or
            # created, along with all dependent objects and containers
            if "region" in processed_obj_data:
                rname = processed_obj_data["region"]
                for r in wb.regions:
                    if hasattr(r, "name") and r.name == rname:
                        break
                else:
                    number = max([0] + [r.number for r in wb.regions]) + 1
                    r = Region(wb, number)
                    r.name = rname
                processed_obj_data["region"] = r
            if otype == "region" and "string_main" in processed_obj_data:
                rname = processed_obj_data["string_main"]
                for r in wb.regions:
                    if hasattr(r, "name") and r.name == rname:
                        break
                else:
                    number = max([0] + [r.number for r in wb.regions]) + 1
                    r = Region(wb, number)
                    r.name = rname
                processed_obj_data["region"] = r
            if "area" in processed_obj_data:
                area_num = processed_obj_data["area"]
                try:
                    a = wb.area(area_num)
                except GridObjDNE:
                    if "region" in processed_obj_data:
                        r = processed_obj_data["region"]
                    else:
                        if len(list(wb.regions)) == 0:
                            r = Region(wb, 1)
                        else:
                            r = wb.regions[0]
                    a = Area(r, area_num)
                processed_obj_data["area"] = a
            if otype == "area" and "int_main" in processed_obj_data:
                area_num = processed_obj_data["int_main"]
                try:
                    a = wb.area(area_num)
                except GridObjDNE:
                    if "region" in processed_obj_data:
                        r = processed_obj_data["region"]
                    else:
                        if len(list(wb.regions)) == 0:
                            r = Region(wb, 1)
                        else:
                            r = wb.regions[0]
                    a = Area(r, area_num)
                processed_obj_data["area"] = a
            if "sub" in processed_obj_data:
                sub_num = processed_obj_data["sub"]
                try:
                    s = wb.sub(sub_num)
                    # Note, sometimes substations are given without area numbers
                    # and will be put into first area by default
                    # Then when buses are defined, this statement will move the
                    # substation to the appropriate area
                    if otype == "bus" and "area" in processed_obj_data:
                        s.area = processed_obj_data["area"]
                except GridObjDNE:
                    if "area" in processed_obj_data:
                        a = processed_obj_data["area"]
                    else:
                        if len(list(wb.areas)) == 0:
                            if "region" in processed_obj_data:
                                r = processed_obj_data["region"]
                            else:
                                if len(list(wb.regions)) == 0:
                                    r = Region(wb, 1)
                                else:
                                    r = wb.regions[0]
                            a = Area(r, 1)
                        else:
                            a = wb.areas[0]
                    s = None if sub_num == 0 else Sub(a, sub_num)
                if s is None: del processed_obj_data["sub"]
                else: processed_obj_data["sub"] = s
            if otype == "sub" and "int_main" in processed_obj_data:
                sub_num = processed_obj_data["int_main"]
                try:
                    s = wb.sub(sub_num)
                except GridObjDNE:
                    if "area" in processed_obj_data:
                        a = processed_obj_data["area"]
                    else:
                        if len(list(wb.areas)) == 0:
                            if "region" in processed_obj_data:
                                r = processed_obj_data["region"]
                            else:
                                if len(list(wb.regions)) == 0:
                                    r = Region(wb, 1)
                                else:
                                    r = wb.regions[0]
                            a = Area(r, 1)
                        else:
                            a = wb.areas[0]
                    s = Sub(a, sub_num)
                processed_obj_data["sub"] = s
            for bname in ["bus", "from_bus", "to_bus", "int_main"]:
                if bname == "int_main" and otype != "bus":
                    continue
                if bname in processed_obj_data:
                    bus_num = processed_obj_data[bname]
                    try:
                        b = wb.bus(bus_num)
                    except GridObjDNE:
                        if "sub" in processed_obj_data:
                            s = processed_obj_data["sub"]
                        else:
                            sub_num = bus_num
                            try:
                                s = wb.sub(sub_num)
                            except GridObjDNE:
                                if "area" in processed_obj_data:
                                    a = processed_obj_data["area"]
                                else:
                                    if len(list(wb.areas)) == 0:
                                        if "region" in processed_obj_data:
                                            r = processed_obj_data["region"]
                                        else:
                                            if len(list(wb.regions)) == 0:
                                                r = Region(wb, 1)
                                            else:
                                                r = wb.regions[0]
                                        a = Area(r, 1)
                                    else:
                                        a = wb.areas[0]
                                s = Sub(a, sub_num)
                        b = Bus(s, bus_num)
                        Node(b, bus_num)
                    processed_obj_data[bname] = b
            if otype == "gen":
                bus = processed_obj_data["bus"]
                id = processed_obj_data["id"]
                try:
                    g = bus.gen(id)
                except GridObjDNE:
                    g = Gen(bus.nodes[0], id)
                processed_obj_data["gen"] = g
            elif otype == "load":
                bus = processed_obj_data["bus"]
                id = processed_obj_data["id"]
                try:
                    l = bus.load(id)
                except GridObjDNE:
                    l = Load(bus.nodes[0], id)
                processed_obj_data["load"] = l
            elif otype == "shunt":
                bus = processed_obj_data["bus"]
                id = processed_obj_data["id"]
                try:
                    s = bus.shunt(id)
                except GridObjDNE:
                    s = Shunt(bus.nodes[0], id)
                processed_obj_data["shunt"] = s
            elif otype == "branch":
                from_bus = processed_obj_data["from_bus"]
                to_bus = processed_obj_data["to_bus"]
                id = processed_obj_data["id"]
                try:
                    br = from_bus.branch_from(to_bus.number, id)
                except GridObjDNE:
                    br = Branch(from_bus.nodes[0], to_bus.nodes[0], id)
                processed_obj_data["branch"] = br

            # Set all object values
            obj = processed_obj_data[otype]
            for field, value in processed_obj_data.items():
                if field not in list(otypes.values()) + ["node", "id", "from_bus", 
                    "to_bus", "int_main", "string_main"]:
                    setattr(obj, field, value)