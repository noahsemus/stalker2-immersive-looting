"""Graph builder on top of bp_t3d: declare nodes and pins, link(a, b), emit paste text.

Links are written on both ends, so the pasted graph never depends on one-sided LinkedTo.
"""
from bp_t3d import G, head, comment_box, T, F, TGT


class Pin:
    def __init__(self, node, name, cat, sub="None", subcat="", out=False, hidden=False, adv=False, extra=""):
        self.node, self.name, self.cat, self.sub, self.subcat = node, name, cat, sub, subcat
        self.out, self.hidden, self.adv, self.extra, self.id, self.links = out, hidden, adv, extra, G(), []
        self.member_ref = ""   # e.g. MemberParent=...,MemberName="ReceiveTick" for an event's OutputDelegate
        self.container = "None"  # "Array" for array pins
        self.wrapper = False     # TSubclassOf function parameters
        self.ref = False         # by-reference parameter
        self.const = False

    def text(self):
        l = ("LinkedTo=(" + "".join(f"{p.node.name} {p.id}," for p in self.links) + "),") if self.links else ""
        d = 'Direction="EGPD_Output",' if self.out else ""
        return (f'   CustomProperties Pin (PinId={self.id},PinName="{self.name}",{self.extra}{d}'
                f'PinType.PinCategory="{self.cat}",PinType.PinSubCategory="{self.subcat}",'
                f'PinType.PinSubCategoryObject={self.sub},'
                + T.replace("PinType.PinSubCategoryMemberReference=()",
                            f"PinType.PinSubCategoryMemberReference=({self.member_ref})")
                   .replace("PinType.ContainerType=None", f"PinType.ContainerType={self.container}")
                   .replace("PinType.bIsUObjectWrapper=False", f"PinType.bIsUObjectWrapper={self.wrapper}")
                   .replace("PinType.bIsReference=False", f"PinType.bIsReference={self.ref}")
                   .replace("PinType.bIsConst=False", f"PinType.bIsConst={self.const}") + l
                + F % ("True" if self.hidden else "False", "True" if self.adv else "False"))


class Node:
    def __init__(self, graph, klass, name, x, y, comment="", body=()):
        self.klass, self.name, self.x, self.y, self.comment, self.body = klass, name, x, y, comment, list(body)
        self.pins = {}
        graph.nodes.append(self)

    def pin(self, name, cat, **kw):
        p = Pin(self, name, cat, **kw)
        self.pins[name] = p
        return p

    def __getitem__(self, name):
        return self.pins[name]

    def text(self):
        return head(self.klass, self.name, self.x, self.y, self.comment, self.body) + \
            [p.text() for p in self.pins.values()] + ["End Object"]


class Graph:
    def __init__(self):
        self.nodes, self.extra, self.boxes = [], [], []

    def link(self, a, b):
        a.links.append(b)
        b.links.append(a)

    def box(self, name, x, y, w, h, text):
        self.boxes.append([name, x, y, w, h, text])

    def text(self):
        out = list(self.extra)
        for b in self.boxes:
            out += comment_box(*b)
        for n in self.nodes:
            out += n.text()
        return out

    # ---- readable layout -------------------------------------------------------------------------------------
    @staticmethod
    def _size(n):
        """Conservative on-screen size of a node (the editor does not export it): one ~30 px row per visible pin on the
        longer side (the exec pins share the header row), ~7.5 px per character of the widest input + output label,
        room for default-value boxes, and the comment bubble above the node (as wide as its text)."""
        import re as _re
        vis = [p for p in n.pins.values() if not p.hidden and not (p.adv and not p.links)]
        ins = [p for p in vis if not p.out and p.cat != "exec"]
        outs = [p for p in vis if p.out and p.cat != "exec"]
        execs = any(p.cat == "exec" for p in vis)
        label = lambda p: len(_re.sub(r"(?<!^)([A-Z])", r" \1", p.name))   # CamelCase -> "Camel Case"
        win = max([label(p) + (12 if ("DefaultValue" in p.extra and not p.links) else 0) for p in ins] + [0])
        wout = max([label(p) for p in outs] + [0])
        title = 0
        for b in n.body:
            m = _re.search(r'MemberName="([^"]+)"', b)
            if m:
                title = len(_re.sub(r"(?<!^)([A-Z])", r" \1", m.group(1)))
        w = max(160, int(7.5 * max(title + 6, win + wout + 6)) + 40)
        rows = max(len(ins), len(outs)) + (1 if execs else 0)
        h = 44 + 30 * max(rows, 1)
        if n.comment:
            w = max(w, int(7 * len(n.comment)) + 40)
            h += 40
        return w, h

    def layout(self, col_gap=110, row_gap=46, box_gap=260, pad=80):
        """Re-place every node so nothing overlaps and execution flows left to right.

        Each node belongs to the comment box that contained its original position (the smallest one), or to a
        trailing "rest" group. Inside a group, a node's column is its longest-path depth over the links inside the
        group (data producers to the left of their consumers, exec chains left to right); nodes in a column are
        ordered by the average row of what feeds them. Groups are stacked top to bottom in their original order and
        each box is resized to enclose its nodes."""
        def contains(b, n):
            return b[1] <= n.x <= b[1] + b[3] and b[2] <= n.y <= b[2] + b[4]

        groups = {i: [] for i in range(len(self.boxes))}
        home = {}
        for n in self.nodes:
            inside = [i for i, b in enumerate(self.boxes) if contains(b, n)]
            if inside:
                home[id(n)] = min(inside, key=lambda i: self.boxes[i][3] * self.boxes[i][4])
        for _ in range(8):   # a node outside every box joins the box of a node it is linked to
            for n in self.nodes:
                if id(n) in home:
                    continue
                for p in n.pins.values():
                    hit = [home[id(q.node)] for q in p.links if id(q.node) in home]
                    if hit:
                        home[id(n)] = hit[0]
                        break
        rest = []
        for n in self.nodes:
            (groups[home[id(n)]] if id(n) in home else rest).append(n)
        order = sorted(groups, key=lambda i: (self.boxes[i][2], self.boxes[i][1]))
        y_cursor = min([b[2] for b in self.boxes] + [0])
        x0 = min([b[1] for b in self.boxes] + [0])
        for gi in order + [None]:
            members = groups[gi] if gi is not None else rest
            if not members:
                continue
            ids = set(id(n) for n in members)
            preds = {id(n): [] for n in members}
            for n in members:
                for p in n.pins.values():
                    if p.out:
                        for q in p.links:
                            if id(q.node) in ids and q.node is not n:
                                preds[id(q.node)].append(n)
            depth = {id(n): 0 for n in members}
            for _ in range(len(members)):
                changed = False
                for n in members:
                    for m in preds[id(n)]:
                        if depth[id(m)] + 1 > depth[id(n)] and depth[id(m)] + 1 < len(members):
                            depth[id(n)] = depth[id(m)] + 1
                            changed = True
                if not changed:
                    break
            cols = {}
            for n in members:
                cols.setdefault(depth[id(n)], []).append(n)
            top = y_cursor + pad + 40
            x = x0 + pad
            bottom = top
            row_of = {}
            for c in sorted(cols):
                col = cols[c]
                col.sort(key=lambda n: (sum(row_of.get(id(m), n.y) for m in preds[id(n)]) / len(preds[id(n)])) if preds[id(n)] else n.y)
                width = max(self._size(n)[0] for n in col)
                y = top
                for n in col:
                    w, h = self._size(n)
                    n.x, n.y = int(x), int(y + (40 if n.comment else 0))
                    row_of[id(n)] = y
                    y += h + row_gap
                bottom = max(bottom, y)
                x += width + col_gap
            if gi is not None:
                b = self.boxes[gi]
                b[1], b[2], b[3], b[4] = int(x0), int(y_cursor), int(x - x0 + pad), int(bottom - y_cursor + pad)
            y_cursor = bottom + pad + box_gap

    # ---- readable layout, v2: exec rows with local data trees ---------------------------------------------------
    @staticmethod
    def _is_exec(n):
        return any(p.cat == "exec" for p in n.pins.values())

    def _clone(self, n, counter):
        """Copy of a pure node with fresh pin ids; input links are duplicated (the producers gain a link), output
        links are not copied (the caller moves one consumer link over)."""
        c = Node(self, n.klass, n.name.rsplit("_", 1)[0] + f"_{counter}", n.x, n.y, n.comment, n.body)
        for name, p in n.pins.items():
            q = c.pin(name, p.cat, sub=p.sub, subcat=p.subcat, out=p.out, hidden=p.hidden, adv=p.adv, extra=p.extra)
            q.member_ref, q.container, q.wrapper, q.ref, q.const = p.member_ref, p.container, p.wrapper, p.ref, p.const
            if not p.out:
                for src in list(p.links):
                    self.link(src, q)
        return c

    def untangle(self):
        """Give every pure node exactly one consumer link by cloning it (pure nodes are re-evaluated per use anyway),
        so data inputs can sit right next to the node that uses them instead of sending wires across the graph."""
        counter = 60000
        changed = True
        while changed:
            changed = False
            for n in list(self.nodes):
                if self._is_exec(n):
                    continue
                uses = [(p, q) for p in n.pins.values() if p.out for q in p.links]
                for p, q in uses[1:]:
                    counter += 1
                    c = self._clone(n, counter)
                    p.links.remove(q)
                    q.links.remove(p)
                    self.link(c.pins[p.name], q)
                    changed = True

    def layout_tree(self, col_gap=90, row_gap=60, box_gap=300, pad=100):
        """Readable layout: within each comment box, the execution chain runs left to right on a row; every exec
        node's data inputs form a small tree directly to its left (after untangle(), each pure node feeds exactly
        one pin); extra exec outputs (Branch false, Sequence then_1..) start new rows below, indented under the node
        they come from. Boxes are stacked top to bottom and resized to fit."""
        self.untangle()

        def contains(b, n):
            return b[1] <= n.x <= b[1] + b[3] and b[2] <= n.y <= b[2] + b[4]

        execs = [n for n in self.nodes if self._is_exec(n)]
        home = {}
        for n in execs:
            inside = [i for i, b in enumerate(self.boxes) if contains(b, n)]
            if inside:
                home[id(n)] = min(inside, key=lambda i: self.boxes[i][3] * self.boxes[i][4])
        for _ in range(10):
            for n in execs:
                if id(n) in home:
                    continue
                for p in n.pins.values():
                    if p.cat != "exec":
                        continue
                    hit = [home[id(q.node)] for q in p.links if id(q.node) in home]
                    if hit:
                        home[id(n)] = hit[0]
                        break
        groups = {}
        for n in execs:
            groups.setdefault(home.get(id(n), -1), []).append(n)

        def data_children(n):
            out = []
            for p in n.pins.values():
                if not p.out and p.cat != "exec":
                    for q in p.links:
                        if not self._is_exec(q.node) and q.node not in out:
                            out.append(q.node)
            return out

        placed = set()

        def place_tree(n, right, top):
            """Place n's data inputs as a tree whose right edge is `right`, starting at `top`; returns the bottom."""
            y = top
            for c in data_children(n):
                if id(c) in placed:
                    continue
                w, h = self._size(c)
                cx = right - w
                placed.add(id(c))
                sub_bottom = place_tree(c, cx - col_gap // 2, y)
                c.x, c.y = int(cx), int(y + (40 if c.comment else 0))
                y = max(y + h, sub_bottom) + row_gap // 2
            return y

        def tree_width(n):
            best = 0
            for c in data_children(n):
                best = max(best, self._size(c)[0] + col_gap // 2 + tree_width(c))
            return best

        order = sorted(groups, key=lambda i: (self.boxes[i][2], self.boxes[i][1]) if i >= 0 else (1e9, 0))
        y_cursor = min([b[2] for b in self.boxes] + [0])
        x0 = min([b[1] for b in self.boxes] + [0])
        for gi in order:
            members = groups[gi]
            ids = set(id(n) for n in members)
            has_in = set()
            for n in members:
                for p in n.pins.values():
                    if p.cat == "exec" and p.out:
                        for q in p.links:
                            if id(q.node) in ids:
                                has_in.add(id(q.node))
            roots = [n for n in members if id(n) not in has_in] or members[:1]
            roots.sort(key=lambda n: (n.y, n.x))
            state = {"bottom": y_cursor + pad + 40}

            def run(n, x, top):
                """Place exec node n with its data tree starting at x on the row at `top`, then follow its exec
                outputs: the first continues the row, the others open rows below."""
                if id(n) in placed or id(n) not in ids:
                    return
                placed.add(id(n))
                tw = tree_width(n)
                w, h = self._size(n)
                nx = x + tw
                n.x, n.y = int(nx), int(top + (40 if n.comment else 0))
                tree_bottom = place_tree(n, nx - col_gap // 2, top) if tw else top
                state["bottom"] = max(state["bottom"], top + h + 40, tree_bottom)
                outs = [p for p in n.pins.values() if p.cat == "exec" and p.out and p.links]
                first = True
                for p in outs:
                    for q in p.links:
                        if id(q.node) in placed or id(q.node) not in ids:
                            continue
                        if first:
                            run(q.node, nx + w + col_gap, top)
                            first = False
                        else:
                            run(q.node, nx + w + col_gap, state["bottom"] + row_gap)

            for r in roots:
                run(r, x0 + pad, state["bottom"] + (row_gap if r is not roots[0] else 0))
            # pure nodes not reached (feeding nodes outside this box): park them under the box
            right = max([n.x + self._size(n)[0] for n in members] + [x0])
            if gi >= 0:
                b = self.boxes[gi]
                b[1], b[2], b[3], b[4] = int(x0), int(y_cursor), int(right - x0 + pad), int(state["bottom"] - y_cursor + pad)
            y_cursor = state["bottom"] + pad + box_gap
        # anything still unplaced (pure nodes whose consumer sits elsewhere): next to its consumer
        for n in self.nodes:
            if id(n) in placed or self._is_exec(n):
                continue
            cons = [q.node for p in n.pins.values() if p.out for q in p.links]
            if cons:
                c = cons[0]
                n.x, n.y = int(c.x - self._size(n)[0] - col_gap), int(c.y + 60)
