"""RED-initial for review F1 of #48: the previous text of 3.2 said that inside a class the FIRST rule violated in READING ORDER wins. The implementation of that statement (spec_classifier.py with
CIC_SPEC_PLANT=class-reading-order-spec, the class operators detected where the scan reaches them) is compared with the prototype, which the older design text (F2 of #46: the operator check runs
before the range rules) describes. The review's two examples must DISAGREE: that is the proof that the previous text did not describe the verdict. Exit 0: the previous text is shown wrong on
both examples; exit 1: it is not (nothing is demonstrated); exit 2: infrastructure."""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = ["[^a&&b]", "[z-a&&b]"]
CHILD = r"""
import sys
sys.argv = ['x']
import spec_classifier as SP, pattern_codes as C
for p in %r:
    print(p, '|', C.classify(p)[0], '|', SP.classify(p))
""" % (CASES,)


def main():
    env = dict(os.environ, CIC_SPEC_PLANT="class-reading-order-spec")
    env.pop("CIC_CODES_PLANT", None)
    r = subprocess.run([sys.executable, "-c", CHILD], capture_output=True, text=True, cwd=HERE, env=env, timeout=120)
    if r.returncode != 0:
        print("INCOMPLETE: %s" % (r.stderr or r.stdout)[-300:]); return 2
    shown = 0
    for line in r.stdout.splitlines():
        p, proto, old = [x.strip() for x in line.split("|")]
        dis = proto != old
        shown += dis
        print("%-9s %-12s prototype (the verdict) = %-28s previous text (reading order) = %-28s" % ("DISAGREE" if dis else "agree", p, proto, old))
    if shown == len(CASES):
        print("RED shown: the previous text of 3.2 contradicts the verdict on both examples of the review")
        return 0
    print("NOT RED: the previous text does not contradict the verdict on every example")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print("INCOMPLETE: %r" % (e,)); sys.exit(2)
