import re

from grblogtools.parsers.util import convert_data_types, typeconvert_groupdict

float_pattern = r"[-+]?((\d*\.\d+)|(\d+\.?))([Ee][+-]?\d+)?"


class NodeLogParser:
    tree_search_start = re.compile(r" Expl Unexpl(.*)It/Node Time$")
    tree_search_explored = re.compile(
        r"Explored (?P<NodeCount>\d+) nodes \((?P<IterCount>\d+) simplex iterations\) in (?P<Runtime>[^\s]+) seconds"
    )
    tree_search_termination = re.compile(
        r"Best objective (?P<ObjVal>[^,]+), best bound (?P<ObjBound>[^,]+), gap (?P<MIPGap>.*)$"
    )

    line_types = [
        # tree_search_full_log_line_regex
        re.compile(
            r"\s\s*(?P<CurrentNode>\d+)\s+(?P<RemainingNodes>\d+)\s+(?P<Obj>{0})\s+(?P<Depth>\d+)\s+(?P<IntInf>\d+)\s+(?P<Incumbent>({0}|-))\s+(?P<BestBd>{0})\s+(?P<Gap>(-|{0}%))\s+(?P<ItPerNode>({0}|-))\s+(?P<Time>\d+)s".format(
                float_pattern
            )
        ),
        # tree_search_nodepruned_line_regex
        re.compile(
            r"\s\s*(?P<CurrentNode>\d+)\s+(?P<RemainingNodes>\d+)\s+(?P<Pruned>(cutoff|infeasible|postponed))\s+(?P<Depth>\d+)\s+(?P<Incumbent>(-|{0}))\s+(?P<BestBd>{0})\s+(?P<Gap>(-|{0}%))\s+(?P<ItPerNode>({0}|-))\s+(?P<Time>\d+)s".format(
                float_pattern
            )
        ),
        # tree_search_new_solution_heuristic_log_line_regex
        re.compile(
            r"(?P<NewSolution>H)\s*(?P<CurrentNode>\d+)\s+(?P<RemainingNodes>\d+)\s+(?P<Incumbent>({0}|-))\s+(?P<BestBd>{0})\s+(?P<Gap>{0}%)\s+(?P<ItPerNode>(-|{0}))\s+(?P<Time>\d+)s".format(
                float_pattern
            )
        ),
        # tree_search_new_solution_branching_log_line_regex
        re.compile(
            r"(?P<NewSolution>\*)\s*(?P<CurrentNode>\d+)\s+(?P<RemainingNodes>\d+)\s+(?P<Depth>\d+)\s+(?P<Incumbent>({0}|-))\s+(?P<BestBd>{0})\s+(?P<Gap>{0}%)\s+(?P<ItPerNode>({0}|-))\s+(?P<Time>\d+)s".format(
                float_pattern
            )
        ),
        # tree_search_status_line_regex
        # not sure what this one is for, nothing in testing?
        # re.compile(
        #     r"\s\s*(?P<CurrentNode>\d+)\s+(?P<RemainingNodes>\d+)\s+(?P<Obj>-)\s+(?P<Depth>\d+)\s+(?P<Incumbent>({0}|-))\s+(?P<BestBd>{0})\s+(?P<Gap>(-|{0}%))\s+(?P<ItPerNode>({0}|-))\s+(?P<Time>\d+)s".format(
        #         float_pattern
        #     )
        # ),
    ]
    cut_report_start = re.compile(r"Cutting planes:")
    cut_report_line = re.compile(r"  (?P<Name>[\w\- ]+): (?P<Count>\d+)")

    def __init__(self):
        """Initialize the NodeLog parser."""
        self._summary = {}
        self._cuts = {}
        self._progress = []
        self._in_cut_report = False
        self._started = False
        # Used to store the data for the last entry of the progress list
        self._progress_last_entry = {}

    def get_summary(self) -> dict:
        """Return the current parsed summary."""
        summary = self._summary
        summary.update({f"Cuts: {name}": count for name, count in self._cuts.items()})
        return summary

    def parse(self, line: str) -> bool:
        """Parse the given log line to populate summary and progress data.

        Args:
            line (str): A line in the log file.

        Returns:
            bool: Return True if the given line is matched by some pattern.
        """
        if not self._started:
            match = self.tree_search_start.match(line)
            if match:
                self._started = True
                return True
            return False

        for regex in self.line_types:
            match = regex.match(line)
            if match:
                self._progress.append(typeconvert_groupdict(match))
                return True

        match = self.tree_search_explored.match(line)
        if match:
            entry = typeconvert_groupdict(match)
            self._summary.update(entry)
            self._progress_last_entry.update(
                {
                    "CurrentNode": entry["NodeCount"],
                    "Time": entry["Runtime"],
                }
            )
            return True

        match = self.tree_search_termination.match(line)
        if match:
            entry = typeconvert_groupdict(match)
            self._summary.update(entry)
            self._progress_last_entry.update(
                {
                    "Incumbent": entry["ObjVal"],
                    "BestBd": entry["ObjBound"],
                    "Gap": entry["MIPGap"],
                }
            )
            self._progress.append(self._progress_last_entry)
            return True

        match = self.cut_report_start.match(line)
        if match:
            self._in_cut_report = True
            return True

        if self._in_cut_report:
            match = self.cut_report_line.match(line)
            if match:
                self._cuts[match.group("Name")] = convert_data_types(
                    match.group("Count")
                )
                return True
        return False

    def get_progress(self) -> list:
        """Return the progress of the search tree."""
        return self._progress
