from dataclasses import dataclass, field
from itertools import combinations


@dataclass
class HintResult:
	cell: tuple[int, int]          # (row, col) being solved
	value: int                     # the number that goes there
	technique: str                 # e.g. "Naked Single"
	explanation: str               # human-readable German text
	highlight_cells: list[tuple] = field(default_factory=list)


# techniques allowed per difficulty tier
TIER_TECHNIQUES = {
	"basic": [
		"naked_single",
		"hidden_single",
	],
	"advanced": [
		"naked_single",
		"hidden_single",
		"naked_pair",
		"naked_triple",
		"pointing_pair",
		"box_line_reduction",
	],
	"expert": [
		"naked_single",
		"hidden_single",
		"naked_pair",
		"naked_triple",
		"pointing_pair",
		"box_line_reduction",
		"x_wing",
		"swordfish",
		"xy_wing",
	],
}

DIFFICULTY_TIER = {
	"Leicht": "basic",
	"Mittel": "basic",
	"Schwer": "advanced",
	"Experte": "advanced",
	"Meister": "expert",
	"Extrem": "expert",
}


class SudokuSolver:
	def __init__(self, board, difficulty="Leicht"):
		self.board = board
		self.difficulty = difficulty
		self.candidates = self._compute_candidates()

	def _compute_candidates(self):
		"""Build candidate sets for all empty cells."""
		cands = [[set() for _ in range(9)] for _ in range(9)]
		for r in range(9):
			for c in range(9):
				if self.board[r][c] == 0:
					cands[r][c] = self._cell_candidates(r, c)
		return cands

	def _cell_candidates(self, row, col):
		"""Compute valid candidates for a single cell."""
		if self.board[row][col] != 0:
			return set()
		used = set()
		# row + col
		for i in range(9):
			used.add(self.board[row][i])
			used.add(self.board[i][col])
		# box
		br, bc = 3 * (row // 3), 3 * (col // 3)
		for r in range(br, br + 3):
			for c in range(bc, bc + 3):
				used.add(self.board[r][c])
		used.discard(0)
		return set(range(1, 10)) - used

	# --- unit helpers ---

	@staticmethod
	def _row_cells(r):
		return [(r, c) for c in range(9)]

	@staticmethod
	def _col_cells(c):
		return [(r, c) for r in range(9)]

	@staticmethod
	def _box_cells(r, c):
		br, bc = 3 * (r // 3), 3 * (c // 3)
		return [(br + dr, bc + dc) for dr in range(3) for dc in range(3)]

	def _units_for(self, r, c):
		"""All three units (row, col, box) containing (r, c)."""
		return [self._row_cells(r), self._col_cells(c), self._box_cells(r, c)]

	@staticmethod
	def _unit_name(unit):
		"""German name for a unit based on its shape."""
		rows = {r for r, c in unit}
		cols = {c for r, c in unit}
		if len(rows) == 1:
			return f"Zeile {list(rows)[0] + 1}"
		if len(cols) == 1:
			return f"Spalte {list(cols)[0] + 1}"
		# box - identify by top-left
		r, c = min(unit)
		box_num = (r // 3) * 3 + (c // 3) + 1
		return f"Block {box_num}"

	# --- main hint entry point ---

	def find_hint(self, target_cell=None, only_target=False):
		"""Find a hint using the simplest technique possible.
		If only_target is True, only try to explain the target cell.
		Returns HintResult or None (caller should use fallback)."""
		tier = DIFFICULTY_TIER.get(self.difficulty, "basic")
		allowed = TIER_TECHNIQUES[tier]

		# iterate techniques in outer loop to always return simplest explanation
		for tech in allowed:
			method = getattr(self, f"_technique_{tech}")
			# try target cell first
			if target_cell:
				r, c = target_cell
				if self.board[r][c] == 0:
					result = method(r, c)
					if result:
						return result
			if only_target:
				continue
			# scan all other empty cells
			for r in range(9):
				for c in range(9):
					if self.board[r][c] == 0 and (r, c) != target_cell:
						result = method(r, c)
						if result:
							return result
		return None

	# --- basic techniques ---

	def _technique_naked_single(self, row, col):
		"""Cell has only one candidate."""
		cands = self.candidates[row][col]
		if len(cands) != 1:
			return None

		val = list(cands)[0]
		# evidence: filled cells in same row/col/box
		evidence = []
		for unit in self._units_for(row, col):
			for r, c in unit:
				if self.board[r][c] != 0 and (r, c) != (row, col):
					evidence.append((r, c))

		# collect eliminated values per unit
		row_vals = sorted({self.board[row][c] for c in range(9) if self.board[row][c] != 0})
		col_vals = sorted({self.board[r][col] for r in range(9) if self.board[r][col] != 0})
		br, bc = 3 * (row // 3), 3 * (col // 3)
		box_vals = sorted({self.board[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3) if self.board[r][c] != 0})
		all_blocked = sorted(set(row_vals + col_vals + box_vals))
		blocked_str = ", ".join(str(v) for v in all_blocked)
		box_num = (row // 3) * 3 + (col // 3) + 1

		explanation = (
			f"Zeile {row + 1}, Spalte {col + 1} und Block {box_num} "
			f"enthalten bereits {blocked_str} - nur {val} ist hier möglich."
		)

		return HintResult(
			cell=(row, col),
			value=val,
			technique="Naked Single",
			explanation=explanation,
			highlight_cells=list(set(evidence)),
		)

	def _technique_hidden_single(self, row, col):
		"""Candidate appears in only one cell within a unit."""
		cands = self.candidates[row][col]
		if not cands:
			return None

		for unit in self._units_for(row, col):
			unit_name = self._unit_name(unit)
			for val in cands:
				# count cells in this unit that can hold val
				positions = [(r, c) for r, c in unit if val in self.candidates[r][c]]
				if len(positions) == 1 and positions[0] == (row, col):
					# evidence: filled cells in the unit that block other positions
					evidence = [(r, c) for r, c in unit
						if (r, c) != (row, col) and self.board[r][c] != 0]
					explanation = (
						f"{val} kann in {unit_name} nur in dieses Feld "
						f"- alle anderen Positionen sind blockiert."
					)
					return HintResult(
						cell=(row, col),
						value=val,
						technique="Hidden Single",
						explanation=explanation,
						highlight_cells=evidence,
					)
		return None

	# --- elimination techniques ---
	# These eliminate candidates, then check if target cell becomes a naked single.

	def _check_naked_single_after_elimination(self, row, col, cands_copy):
		"""After modifying cands_copy, check if (row, col) has exactly one candidate."""
		if len(cands_copy[row][col]) == 1:
			return list(cands_copy[row][col])[0]
		return None

	def _deep_copy_candidates(self):
		return [[cell.copy() for cell in row] for row in self.candidates]

	def _technique_naked_pair(self, row, col):
		"""Two cells in a unit share exactly two candidates, eliminating from others."""
		cands = self.candidates[row][col]
		if not cands or len(cands) > 3:
			return None

		for unit in self._units_for(row, col):
			unit_name = self._unit_name(unit)
			# find pairs of cells with exactly 2 candidates that match
			bi_cells = [(r, c) for r, c in unit if len(self.candidates[r][c]) == 2]
			for a, b in combinations(bi_cells, 2):
				if self.candidates[a[0]][a[1]] != self.candidates[b[0]][b[1]]:
					continue
				pair_vals = self.candidates[a[0]][a[1]]
				# check if elimination affects target cell
				if (row, col) == a or (row, col) == b:
					continue  # target is part of the pair, no elimination
				if not (pair_vals & cands):
					continue  # nothing to eliminate from target

				# simulate elimination
				cands_copy = self._deep_copy_candidates()
				eliminated = False
				for r, c in unit:
					if (r, c) != a and (r, c) != b:
						before = len(cands_copy[r][c])
						cands_copy[r][c] -= pair_vals
						if len(cands_copy[r][c]) < before:
							eliminated = True

				if not eliminated:
					continue
				val = self._check_naked_single_after_elimination(row, col, cands_copy)
				if val is None:
					continue

				pair_str = ", ".join(str(v) for v in sorted(pair_vals))
				explanation = (
					f"In {unit_name} haben zwei Felder nur die Kandidaten {{{pair_str}}}. "
					f"Diese Werte werden aus den anderen Feldern eliminiert - "
					f"nur {val} bleibt hier übrig."
				)
				return HintResult(
					cell=(row, col),
					value=val,
					technique="Naked Pair",
					explanation=explanation,
					highlight_cells=[a, b],
				)
		return None

	def _technique_naked_triple(self, row, col):
		"""Three cells in a unit have candidates that are a subset of three values."""
		cands = self.candidates[row][col]
		if not cands:
			return None

		for unit in self._units_for(row, col):
			unit_name = self._unit_name(unit)
			# cells with 2-3 candidates
			small_cells = [(r, c) for r, c in unit if 1 <= len(self.candidates[r][c]) <= 3]
			for combo in combinations(small_cells, 3):
				union = set()
				for r, c in combo:
					union |= self.candidates[r][c]
				if len(union) != 3:
					continue
				# target must not be part of the triple
				if (row, col) in combo:
					continue
				if not (union & cands):
					continue

				# simulate elimination
				cands_copy = self._deep_copy_candidates()
				eliminated = False
				for r, c in unit:
					if (r, c) not in combo:
						before = len(cands_copy[r][c])
						cands_copy[r][c] -= union
						if len(cands_copy[r][c]) < before:
							eliminated = True

				if not eliminated:
					continue
				val = self._check_naked_single_after_elimination(row, col, cands_copy)
				if val is None:
					continue

				triple_str = ", ".join(str(v) for v in sorted(union))
				explanation = (
					f"In {unit_name} enthalten drei Felder nur die Kandidaten {{{triple_str}}}. "
					f"Diese Werte werden eliminiert - nur {val} bleibt hier übrig."
				)
				return HintResult(
					cell=(row, col),
					value=val,
					technique="Naked Triple",
					explanation=explanation,
					highlight_cells=list(combo),
				)
		return None

	def _technique_pointing_pair(self, row, col):
		"""Candidate in a box confined to one row/col, eliminates from rest of that row/col."""
		cands = self.candidates[row][col]
		if not cands:
			return None

		# check each box
		for box_r_start in range(0, 9, 3):
			for box_c_start in range(0, 9, 3):
				box = self._box_cells(box_r_start, box_c_start)
				for val in range(1, 10):
					positions = [(r, c) for r, c in box if val in self.candidates[r][c]]
					if len(positions) < 2:
						continue

					rows_in = {r for r, c in positions}
					cols_in = {c for r, c in positions}

					line_cells = None
					line_name = None

					# confined to one row
					if len(rows_in) == 1:
						lr = list(rows_in)[0]
						line_cells = self._row_cells(lr)
						line_name = f"Zeile {lr + 1}"
					# confined to one col
					elif len(cols_in) == 1:
						lc = list(cols_in)[0]
						line_cells = self._col_cells(lc)
						line_name = f"Spalte {lc + 1}"
					else:
						continue

					# eliminate val from line cells outside this box
					cands_copy = self._deep_copy_candidates()
					eliminated = False
					for r, c in line_cells:
						if (r, c) not in positions and val in cands_copy[r][c]:
							cands_copy[r][c].discard(val)
							eliminated = True

					if not eliminated:
						continue
					result_val = self._check_naked_single_after_elimination(row, col, cands_copy)
					if result_val is None:
						continue

					box_num = (box_r_start // 3) * 3 + (box_c_start // 3) + 1
					explanation = (
						f"{val} kann in Block {box_num} nur in {line_name} stehen "
						f"und wird aus dem Rest der {line_name.split()[0]} eliminiert."
					)
					return HintResult(
						cell=(row, col),
						value=result_val,
						technique="Pointing Pair",
						explanation=explanation,
						highlight_cells=positions,
					)
		return None

	def _technique_box_line_reduction(self, row, col):
		"""Candidate in a row/col confined to one box, eliminates from rest of that box."""
		cands = self.candidates[row][col]
		if not cands:
			return None

		lines = []
		for r in range(9):
			lines.append(("Zeile", r, self._row_cells(r)))
		for c in range(9):
			lines.append(("Spalte", c, self._col_cells(c)))

		for line_type, line_idx, line in lines:
			for val in range(1, 10):
				positions = [(r, c) for r, c in line if val in self.candidates[r][c]]
				if len(positions) < 2:
					continue

				# check if all in same box
				boxes = {(r // 3, c // 3) for r, c in positions}
				if len(boxes) != 1:
					continue

				box_r, box_c = list(boxes)[0]
				box = self._box_cells(box_r * 3, box_c * 3)

				# eliminate from rest of box
				cands_copy = self._deep_copy_candidates()
				eliminated = False
				for r, c in box:
					if (r, c) not in positions and val in cands_copy[r][c]:
						cands_copy[r][c].discard(val)
						eliminated = True

				if not eliminated:
					continue
				result_val = self._check_naked_single_after_elimination(row, col, cands_copy)
				if result_val is None:
					continue

				box_num = box_r * 3 + box_c + 1
				line_name = f"{line_type} {line_idx + 1}"
				explanation = (
					f"{val} kann in {line_name} nur in Block {box_num} stehen "
					f"und wird aus dem Rest des Blocks eliminiert."
				)
				return HintResult(
					cell=(row, col),
					value=result_val,
					technique="Box/Line Reduction",
					explanation=explanation,
					highlight_cells=positions,
				)
		return None

	def _technique_x_wing(self, row, col):
		"""Candidate in exactly 2 positions in 2 rows forming a rectangle."""
		cands = self.candidates[row][col]
		if not cands:
			return None

		# try rows first, then cols
		for val in range(1, 10):
			result = self._find_x_wing(row, col, val, by_row=True)
			if result:
				return result
			result = self._find_x_wing(row, col, val, by_row=False)
			if result:
				return result
		return None

	def _find_x_wing(self, row, col, val, by_row=True):
		"""Helper for X-Wing: find two rows/cols with val in exactly 2 matching positions."""
		# collect lines with exactly 2 positions for val
		lines_with_two = []
		for i in range(9):
			if by_row:
				line = self._row_cells(i)
			else:
				line = self._col_cells(i)
			positions = [(r, c) for r, c in line if val in self.candidates[r][c]]
			if len(positions) == 2:
				lines_with_two.append((i, positions))

		for (i1, pos1), (i2, pos2) in combinations(lines_with_two, 2):
			# check if same secondary positions
			if by_row:
				sec1 = {c for _, c in pos1}
				sec2 = {c for _, c in pos2}
			else:
				sec1 = {r for r, _ in pos1}
				sec2 = {r for r, _ in pos2}
			if sec1 != sec2:
				continue

			# eliminate from the perpendicular lines
			cands_copy = self._deep_copy_candidates()
			eliminated = False
			all_positions = pos1 + pos2
			for sec_idx in sec1:
				if by_row:
					perp = self._col_cells(sec_idx)
				else:
					perp = self._row_cells(sec_idx)
				for r, c in perp:
					if (r, c) not in all_positions and val in cands_copy[r][c]:
						cands_copy[r][c].discard(val)
						eliminated = True

			if not eliminated:
				continue
			result_val = self._check_naked_single_after_elimination(row, col, cands_copy)
			if result_val is None:
				continue

			if by_row:
				line_desc = f"Zeilen {i1 + 1} und {i2 + 1}"
				elim_desc = "Spalten"
			else:
				line_desc = f"Spalten {i1 + 1} und {i2 + 1}"
				elim_desc = "Zeilen"
			explanation = (
				f"{val} bildet ein X-Wing-Muster in {line_desc} "
				f"und wird aus den entsprechenden {elim_desc} eliminiert."
			)
			return HintResult(
				cell=(row, col),
				value=result_val,
				technique="X-Wing",
				explanation=explanation,
				highlight_cells=all_positions,
			)
		return None

	def _technique_swordfish(self, row, col):
		"""Like X-Wing but with 3 rows/columns."""
		cands = self.candidates[row][col]
		if not cands:
			return None

		for val in range(1, 10):
			result = self._find_swordfish(row, col, val, by_row=True)
			if result:
				return result
			result = self._find_swordfish(row, col, val, by_row=False)
			if result:
				return result
		return None

	def _find_swordfish(self, row, col, val, by_row=True):
		"""Helper for Swordfish: 3 rows/cols with val in 2-3 positions spanning exactly 3 secondary lines."""
		lines = []
		for i in range(9):
			if by_row:
				line = self._row_cells(i)
			else:
				line = self._col_cells(i)
			positions = [(r, c) for r, c in line if val in self.candidates[r][c]]
			if 2 <= len(positions) <= 3:
				if by_row:
					secs = frozenset(c for _, c in positions)
				else:
					secs = frozenset(r for r, _ in positions)
				lines.append((i, positions, secs))

		for combo in combinations(lines, 3):
			union_secs = combo[0][2] | combo[1][2] | combo[2][2]
			if len(union_secs) != 3:
				continue

			all_positions = combo[0][1] + combo[1][1] + combo[2][1]

			# eliminate from secondary lines
			cands_copy = self._deep_copy_candidates()
			eliminated = False
			for sec_idx in union_secs:
				if by_row:
					perp = self._col_cells(sec_idx)
				else:
					perp = self._row_cells(sec_idx)
				for r, c in perp:
					if (r, c) not in all_positions and val in cands_copy[r][c]:
						cands_copy[r][c].discard(val)
						eliminated = True

			if not eliminated:
				continue
			result_val = self._check_naked_single_after_elimination(row, col, cands_copy)
			if result_val is None:
				continue

			idxs = sorted(c[0] + 1 for c in combo)
			if by_row:
				line_desc = f"Zeilen {idxs[0]}, {idxs[1]} und {idxs[2]}"
				elim_desc = "Spalten"
			else:
				line_desc = f"Spalten {idxs[0]}, {idxs[1]} und {idxs[2]}"
				elim_desc = "Zeilen"
			explanation = (
				f"{val} bildet ein Swordfish-Muster in {line_desc} "
				f"und wird aus den entsprechenden {elim_desc} eliminiert."
			)
			return HintResult(
				cell=(row, col),
				value=result_val,
				technique="Swordfish",
				explanation=explanation,
				highlight_cells=all_positions,
			)
		return None

	def _technique_xy_wing(self, row, col):
		"""Three bi-value cells forming pivot+wings pattern."""
		cands = self.candidates[row][col]
		if not cands:
			return None

		# collect all bi-value cells
		bi_cells = []
		for r in range(9):
			for c in range(9):
				if len(self.candidates[r][c]) == 2:
					bi_cells.append((r, c))

		# try each bi-value cell as pivot
		for pr, pc in bi_cells:
			pivot_cands = self.candidates[pr][pc]
			if len(pivot_cands) != 2:
				continue
			a, b = sorted(pivot_cands)

			# find wings that see the pivot
			visible = self._visible_cells(pr, pc)
			wings_for_a = []  # cells with {a, z} for some z != b
			wings_for_b = []  # cells with {b, z} for some z != a

			for wr, wc in visible:
				if len(self.candidates[wr][wc]) != 2:
					continue
				w_cands = self.candidates[wr][wc]
				if a in w_cands and b not in w_cands:
					wings_for_a.append((wr, wc))
				elif b in w_cands and a not in w_cands:
					wings_for_b.append((wr, wc))

			# pair wings: wing1 has {a, z}, wing2 has {b, z}
			for w1r, w1c in wings_for_a:
				z1 = (self.candidates[w1r][w1c] - {a}).pop()
				for w2r, w2c in wings_for_b:
					z2 = (self.candidates[w2r][w2c] - {b}).pop()
					if z1 != z2:
						continue
					z = z1
					# wings must not see each other (standard XY-Wing)
					# eliminate z from cells that see both wings
					w1_visible = set(self._visible_cells(w1r, w1c))
					w2_visible = set(self._visible_cells(w2r, w2c))
					common = w1_visible & w2_visible

					cands_copy = self._deep_copy_candidates()
					eliminated = False
					for r, c in common:
						if (r, c) != (pr, pc) and z in cands_copy[r][c]:
							cands_copy[r][c].discard(z)
							eliminated = True

					if not eliminated:
						continue
					result_val = self._check_naked_single_after_elimination(row, col, cands_copy)
					if result_val is None:
						continue

					explanation = (
						f"XY-Wing mit Pivot in Zeile {pr + 1}/Spalte {pc + 1}: "
						f"{z} wird aus gemeinsam sichtbaren Feldern eliminiert."
					)
					return HintResult(
						cell=(row, col),
						value=result_val,
						technique="XY-Wing",
						explanation=explanation,
						highlight_cells=[(pr, pc), (w1r, w1c), (w2r, w2c)],
					)
		return None

	def _visible_cells(self, row, col):
		"""All cells that share a row, col, or box with (row, col), excluding itself."""
		seen = set()
		for unit in self._units_for(row, col):
			for r, c in unit:
				if (r, c) != (row, col):
					seen.add((r, c))
		return list(seen)
