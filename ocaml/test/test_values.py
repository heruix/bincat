import pytest
import subprocess
import copy
import binascii
import os.path
import itertools
from pybincat import cfa

def counter(fmt="%i", i=0):
    while True:
        yield fmt % i
        i += 1

GCC_DIR = counter("gcc-%i")
NASM_DIR = counter("nasm-%i")

ALL_FLAGS = ["cf","pf", "af", "zf","sf","df","of"]
ALL_REGS = ["eax","ebx","ecx","edx", "esi","edi","esp", "ebp"] + ALL_FLAGS

def assemble(tmpdir, asm):
    d = tmpdir.mkdir(NASM_DIR.next())
    inf = d.join("asm.S")
    outf = d.join("opcodes")
    inf.write("BITS 32\n"+asm)
    p = subprocess.Popen(["nasm", "-o", str(outf), str(inf)])
    p.wait()
    return str(outf)


C_TEMPLATE_PROLOGUE = r"""
#include <stdio.h>
void main(void)
{
        unsigned int Reax,Rebx,Recx,Redx,Resi,Redi,Resp,Rebp,Reflags;
        asm volatile(
"""

C_TEMPLATE_EPILOGUE = r""" 
        "mov %0, eax\n"
        "mov %1, esp\n"
        "mov %2, ebp\n"
        "pushf\n"
        "pop eax\n"
        : 
        "=m" (Reax),
        "=m" (Resp),
        "=m" (Rebp),
        "=a" (Reflags),
        "=b" (Rebx),
        "=c" (Recx),
        "=d" (Redx),
        "=S" (Resi),
        "=D" (Redi)
        ::);
        printf("eax=%08x\n", Reax);
        printf("ebx=%08x\n", Rebx);
        printf("ecx=%08x\n", Recx);
        printf("edx=%08x\n", Redx);
        printf("esi=%08x\n", Resi);
        printf("edi=%08x\n", Redi);
        printf("esp=%08x\n", Resp);
        printf("ebp=%08x\n", Rebp);
        printf("eflags=%08x\n", Reflags);
}
"""

def cpu_run(tmpdir, asm):
    d = tmpdir.mkdir(GCC_DIR.next())
    inf = d.join("test.c")
    outf = d.join("test")
    inf.write(C_TEMPLATE_PROLOGUE +
              '"'+asm.replace("\n",'\\n"\n"') + '"' +
              C_TEMPLATE_EPILOGUE)
    subprocess.check_call(["gcc", "-m32", "-masm=intel", "-o", str(outf), str(inf)])
    out = subprocess.check_output([str(outf)])
    regs = { reg: int(val,16) for reg, val in
            (l.strip().split("=") for l in out.splitlines()) }
    flags = regs.pop("eflags")
    regs["cf"] = flags & 1
    regs["pf"] = (flags >> 2) & 1
    regs["af"] = (flags >> 4) & 1
    regs["zf"] = (flags >> 6) & 1
    regs["sf"] = (flags >> 7) & 1
    regs["df"] = (flags >> 10) & 1
    regs["of"] = (flags >> 11) & 1
    return regs


def getReg(my_state, name):
    v = cfa.Value('reg', name, cfa.reg_len(name))
    return my_state[v][0]
def getLastState(prgm):
    curState = prgm['0']
    while True:
        nextStates = prgm.next_states(curState.node_id)
        if len(nextStates) == 0:
            return curState
        assert len(nextStates) == 1, \
            "expected exactly 1 destination state after running this instruction"
        curState = nextStates[0]

def prettify(asm):
    s = []
    for l in asm.splitlines():
        l = l.strip()
        if l:
            s.append("\t"+l)
    return "\n".join(s)

def bincat_run(tmpdir, asm):
    opcodesfname = assemble(tmpdir, asm)
    
    outf = tmpdir.join('end.ini')
    logf = tmpdir.join('log.txt')
    initf = tmpdir.join('init.ini')
    initf.write(
        open("test_values.ini").read().format(
            code_length = len(open(opcodesfname).read()),
            filepath = opcodesfname,
        ))
    prgm = cfa.CFA.from_filenames(str(initf), str(outf), str(logf))

    last_state = getLastState(prgm)
    
    return { reg : getReg(last_state, reg) for reg in ALL_REGS}


def compare(tmpdir, asm, regs=ALL_REGS):
    cpu = cpu_run(tmpdir, asm)
    bincat = bincat_run(tmpdir, asm)
    diff = []
    for r in regs:
        vtop = bincat[r].vtop
        value = bincat[r].value
        if cpu[r] & ~vtop != value & ~vtop:
            diff.append("- cpu   :  %s = %08x" % (r, cpu[r]))
            diff.append("+ bincat:  %s = %08x  %r" % (r,value,bincat[r]))
    assert not diff, "\n"+prettify(asm)+"\n=========================\n"+"\n".join(diff)

    

def test_assign(tmpdir):
    asm = """
    	mov eax,0xaaaa55aa
	mov ebx,0xcccccc55
    """
    compare(tmpdir, asm, ["eax","ebx"])


def test_compare(tmpdir):
    asm = """
    	mov eax,0xaaaaffaa
	mov ebx,0xbbbbbbff
        cmp ah,bl
    """
    compare(tmpdir, asm, ["eax","ebx"] + ALL_FLAGS)


def test_rol(tmpdir):
    for i in range(65):
        asm = """
                mov cl,%i
                mov eax,0x12b4e78f
                rol eax,cl
        """ % i
        compare(tmpdir, asm, ["eax", "cf", "of"])

def test_ror(tmpdir):
    for i in range(65):
        asm = """
                mov cl,%i
                mov eax,0x12b4e78f
                ror eax,cl
        """ % i
        compare(tmpdir, asm, ["eax", "cf", "of"])


def test_rcl(tmpdir):
    for i in range(65):
        asm = """
                mov cl,%i
                mov eax,0x12b4e78f
                rcl eax,cl
        """ % i
        compare(tmpdir, "stc\n"+asm, ["eax", "cf", "of"])
        compare(tmpdir, "clc\n"+asm, ["eax", "cf", "of"])

def test_rcr(tmpdir):
    for i in range(65):
        asm = """
                mov cl,%i
                mov eax,0x12b4e78f
                rcr eax,cl
        """ % i
        compare(tmpdir, "stc\n"+asm, ["eax", "cf", "of"])
        compare(tmpdir, "clc\n"+asm, ["eax", "cf", "of"])

SOME_OPERANDS = [ 0, 1, 2, 0x1234, 0x7fff, 0x8000, 0xffff, 0xffffffff, 0x80000000, 0x7fffffff ]
SOME_OPERANDS_COUPLES = list(itertools.product(SOME_OPERANDS, SOME_OPERANDS))

def test_add_reg32(tmpdir):
    asm = """
            mov eax, %#x
            add eax, %#x
          """
    for vals in SOME_OPERANDS_COUPLES:
        compare(tmpdir, asm % vals, ["eax", "of", "sf", "zf", "cf", "pf", "af"])

def test_sub_reg32(tmpdir):
    asm = """
            mov eax, %#x
            sub eax, %#x
          """
    for vals in SOME_OPERANDS_COUPLES:
        compare(tmpdir, asm % vals, ["eax", "of", "sf", "zf", "cf", "pf", "af"])

def test_and_reg32(tmpdir):
    asm = """
            mov eax, %#x
            and eax, %#x
          """
    for vals in SOME_OPERANDS_COUPLES:
        compare(tmpdir, asm % vals, ["eax", "of", "sf", "zf", "cf", "pf", "af"])

def test_mul_reg32(tmpdir):
    asm = """
            mov eax, %#x
            mov ebx, %#x
            mul ebx
          """
    for vals in SOME_OPERANDS_COUPLES:
        compare(tmpdir, asm % vals, ["eax", "edx", "of", "cf"])

def test_imul_reg32(tmpdir):
    asm = """
            mov eax, %#x
            mov ebx, %#x
            imul ebx
          """
    for vals in SOME_OPERANDS_COUPLES:
        compare(tmpdir, asm % vals, ["eax", "edx", "of", "cf"])

