# Independent McNemar Power Audit

Date: 2026-07-19

Command: `python artifact-v2-refresh/audit/independent_power_enum.py`

Runtime: Python 3.12.10 using the standard library only

Status: **PASS**

The audit implementation does not import the repository statistics helper. It
directly enumerates the trinomial task outcomes of favored discordance,
opposing discordance, and concordance. The exact two-sided rejection cells are
derived from integer binomial tails. This is separate from the repository
helper's conditional decomposition over the number of discordant pairs.

Locked inputs are paired risk difference 0.2, discordance rate 0.5, two-sided
alpha 0.05, and target power 0.8.

| Paired tasks | Independently enumerated power | Six decimals |
| ---: | ---: | ---: |
| 8 | 0.0157534438281250 | 0.015753 |
| 15 | 0.098284692405417779541015625000 | 0.098285 |
| 40 | 0.3544332017255859210191788060841765 | 0.354433 |
| 60 | 0.5249353223627349823193535709546102 | 0.524935 |
| 103 | 0.8018189073387435535811494718713288 | 0.801819 |

The script also evaluates every attainable integer count from 1 through 15.
All are inadequate at target power 0.8. The maximum over that range occurs at
15 tasks and is 0.098284692405417779541015625000, which directly verifies the
fallback adequacy check when monotonicity is not assumed.

The 102-pair boundary power is 0.7976421823155200358826829218572645.
The first integer count attaining 0.8 power is therefore 103.

The independently inverted MDE at 0.8 power is
0.3169030957634705435436206581134391 for 40 pairs and
0.2635189467374642005740473312623758 for 60 pairs. These reproduce the
reported 0.317 and 0.264 values. At eight pairs, target power is unattainable
over the allowed effect range and maximum power at risk difference 0.5 is
0.14453125.

For completeness, the script also reproduces the historical arithmetic MDE of
0.2846783560350823711848423049352289 at 51 items that appears in the
superseded unit-accounting-error receipt. This arithmetic agreement does not
validate treating those 51 selected items as paired analysis units.

All comparisons to the receipt's binary64 values pass at absolute tolerance
`5e-15`. The extra trailing digits above come from 70-digit decimal arithmetic.

Implementation SHA-256 hashes:

- Independent enumeration
  `ceb11836339e8d70a3a12622f6686cc52041197186ad93298a04c6247f000b05`
- Repository helper
  `5595dc03905049847cc7111cc72004a9ab31fb075392bc8948d85f2a0fda9aac`
