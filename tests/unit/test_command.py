# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.command as sut
from . import fixtures
import unittest


class AnalyzerTest(unittest.TestCase):

    def test_set_language(self):
        def test(expected, input):
            result = None
            for x in sut._language_check([input]):
                result = x
            self.assertEqual(expected, result)

        l = 'language'
        f = 'file'
        i = 'cxx'
        test({f: 'file.c', l: 'c'}, {f: 'file.c', l: 'c'})
        test({f: 'file.c', l: 'c++'}, {f: 'file.c', l: 'c++'})
        test({f: 'file.c', l: 'c++', i: True}, {f: 'file.c', i: True})
        test({f: 'file.c', l: 'c'}, {f: 'file.c'})
        test({f: 'file.cxx', l: 'c++'}, {f: 'file.cxx'})
        test({f: 'file.i', l: 'c-cpp-output'}, {f: 'file.i'})
        test({f: 'f.i', l: 'c-cpp-output'}, {f: 'f.i', l: 'c-cpp-output'})
        test(None, {f: 'file.java'})

    def test_arch_loop(self):
        def test(input):
            result = []
            for x in sut._arch_check([input]):
                result.append(x)
            return result

        input = {'key': 'value'}
        self.assertEqual([input], test(input))

        input = {'archs_seen': ['-arch', 'i386']}
        self.assertEqual([{'arch': 'i386'}], test(input))

        input = {'archs_seen': ['-arch', 'ppc']}
        self.assertEqual([], test(input))

        input = {'archs_seen': ['-arch', 'i386', '-arch', 'ppc']}
        self.assertEqual([{'arch': 'i386'}], test(input))

        input = {'archs_seen': ['-arch', 'i386', '-arch', 'sparc']}
        result = test(input)
        self.assertTrue(result == [{'arch': 'i386'}] or
                        result == [{'arch': 'sparc'}])


class ParseTest(unittest.TestCase):

    def test_action(self):
        def test(expected, cmd):
            opts = sut.classify_parameters(cmd)
            self.assertEqual(expected, opts['action'])

        Info = sut.Action.Info
        test(Info, ['clang', 'source.c', '-print-prog-name'])

        Link = sut.Action.Link
        test(Link, ['clang', 'source.c'])

        Compile = sut.Action.Compile
        test(Compile, ['clang', '-c', 'source.c'])
        test(Compile, ['clang', '-c', 'source.c', '-MF', 'source.d'])

        Preprocess = sut.Action.Preprocess
        test(Preprocess, ['clang', '-E', 'source.c'])
        test(Preprocess, ['clang', '-c', '-E', 'source.c'])
        test(Preprocess, ['clang', '-c', '-M', 'source.c'])
        test(Preprocess, ['clang', '-c', '-MM', 'source.c'])

    def test_optimalizations(self):
        def test(cmd):
            opts = sut.classify_parameters(cmd)
            return opts.get('compile_options', [])

        self.assertEqual(['-O1'], test(['clang', '-c', 'source.c', '-O']))
        self.assertEqual(['-O1'], test(['clang', '-c', 'source.c', '-O1']))
        self.assertEqual(['-O2'], test(['clang', '-c', 'source.c', '-Os']))
        self.assertEqual(['-O2'], test(['clang', '-c', 'source.c', '-O2']))
        self.assertEqual(['-O3'], test(['clang', '-c', 'source.c', '-O3']))

    def test_language(self):
        def test(cmd):
            opts = sut.classify_parameters(cmd)
            return opts.get('language')

        self.assertEqual(None, test(['clang', '-c', 'source.c']))
        self.assertEqual('c', test(['clang', '-c', 'source.c', '-x', 'c']))
        self.assertEqual('cpp', test(['clang', '-c', 'source.c', '-x', 'cpp']))

    def test_arch(self):
        def test(cmd):
            opts = sut.classify_parameters(cmd)
            return opts.get('archs_seen', [])

        eq = self.assertEqual

        eq([], test(['clang', '-c', 'source.c']))
        eq(['-arch', 'mips'],
           test(['clang', '-c', 'source.c', '-arch', 'mips']))
        eq(['-arch', 'mips', '-arch', 'i386'],
           test(['clang', '-c', 'source.c', '-arch', 'mips', '-arch', 'i386']))

    def test_input_file(self):
        def test(cmd):
            opts = sut.classify_parameters(cmd)
            return opts.get('files', [])

        eq = self.assertEqual

        eq(['src.c'], test(['clang', 'src.c']))
        eq(['src.c'], test(['clang', '-c', 'src.c']))
        eq(['s1.c', 's2.c'], test(['clang', '-c', 's1.c', 's2.c']))

    def test_output_file(self):
        def test(cmd):
            opts = sut.classify_parameters(cmd)
            return opts.get('output', None)

        eq = self.assertEqual

        eq(None, test(['clang', 'src.c']))
        eq('src.o', test(['clang', '-c', 'src.c', '-o', 'src.o']))
        eq('src.o', test(['clang', '-c', '-o', 'src.o', 'src.c']))

    def test_include(self):
        def test(cmd):
            opts = sut.classify_parameters(cmd)
            return opts.get('compile_options', [])

        eq = self.assertEqual

        eq([], test(['clang', '-c', 'src.c']))
        eq(['-include', '/usr/local/include'],
           test(['clang', '-c', 'src.c', '-include', '/usr/local/include']))
        eq(['-I.'],
           test(['clang', '-c', 'src.c', '-I.']))
        eq(['-I', '.'],
           test(['clang', '-c', 'src.c', '-I', '.']))
        eq(['-I/usr/local/include'],
           test(['clang', '-c', 'src.c', '-I/usr/local/include']))
        eq(['-I', '/usr/local/include'],
           test(['clang', '-c', 'src.c', '-I', '/usr/local/include']))
        eq(['-I/opt', '-I', '/opt/otp/include'],
           test(['clang', '-c', 'src.c', '-I/opt', '-I', '/opt/otp/include']))

    def test_define(self):
        def test(cmd):
            opts = sut.classify_parameters(cmd)
            return opts.get('compile_options', [])

        eq = self.assertEqual

        eq([], test(['clang', '-c', 'src.c']))
        eq(['-DNDEBUG'],
           test(['clang', '-c', 'src.c', '-DNDEBUG']))
        eq(['-UNDEBUG'],
           test(['clang', '-c', 'src.c', '-UNDEBUG']))
        eq(['-Dvar1=val1', '-Dvar2=val2'],
           test(['clang', '-c', 'src.c', '-Dvar1=val1', '-Dvar2=val2']))
        eq(['-Dvar="val ues"'],
           test(['clang', '-c', 'src.c', '-Dvar="val ues"']))

    def test_ignored_flags(self):
        def test(cmd):
            salt = ['-I.', '-D_THIS']
            opts = sut.classify_parameters(cmd + salt)
            self.assertEqual(salt, opts.get('compile_options'))
            return opts.get('link_options', [])

        eq = self.assertEqual

        eq([],
           test(['clang', 'src.o']))
        eq([],
           test(['clang', 'src.o', '-lrt', '-L/opt/company/lib']))
        eq([],
           test(['clang', 'src.o', '-framework', 'foo']))

    def test_compile_only_flags(self):
        def test(cmd):
            opts = sut.classify_parameters(cmd)
            return opts.get('compile_options', [])

        eq = self.assertEqual

        eq([], test(['clang', '-c', 'src.c']))
        eq([],
           test(['clang', '-c', 'src.c', '-Wnoexcept']))
        eq([],
           test(['clang', '-c', 'src.c', '-Wall']))
        eq(['-Wno-cpp'],
           test(['clang', '-c', 'src.c', '-Wno-cpp']))
        eq(['-std=C99'],
           test(['clang', '-c', 'src.c', '-std=C99']))
        eq(['-mtune=i386', '-mcpu=i386'],
           test(['clang', '-c', 'src.c', '-mtune=i386', '-mcpu=i386']))
        eq(['-nostdinc'],
           test(['clang', '-c', 'src.c', '-nostdinc']))
        eq(['-isystem', '/image/debian'],
           test(['clang', '-c', 'src.c', '-isystem', '/image/debian']))
        eq(['-iprefix', '/usr/local'],
           test(['clang', '-c', 'src.c', '-iprefix', '/usr/local']))
        eq(['-iquote=me'],
           test(['clang', '-c', 'src.c', '-iquote=me']))
        eq(['-iquote', 'me'],
           test(['clang', '-c', 'src.c', '-iquote', 'me']))

    def test_compile_and_link_flags(self):
        def test(cmd):
            opts = sut.classify_parameters(cmd)
            return opts.get('compile_options', [])

        eq = self.assertEqual

        eq([],
           test(['clang', '-c', 'src.c', '-fsyntax-only']))
        eq(['-fsinged-char'],
           test(['clang', '-c', 'src.c', '-fsinged-char']))
        eq(['-fPIC'],
           test(['clang', '-c', 'src.c', '-fPIC']))
        eq(['-stdlib=libc++'],
           test(['clang', '-c', 'src.c', '-stdlib=libc++']))
        eq(['--sysroot', '/'],
           test(['clang', '-c', 'src.c', '--sysroot', '/']))
        eq(['-isysroot', '/'],
           test(['clang', '-c', 'src.c', '-isysroot', '/']))
        eq([],
           test(['clang', '-c', 'src.c', '-sectorder', 'a', 'b', 'c']))

    def test_detect_cxx_from_compiler_name(self):
        def test(cmd):
            opts = sut.classify_parameters(cmd)
            return opts.get('cxx')

        eq = self.assertEqual

        eq(False, test(['cc', '-c', 'src.c']))
        eq(True, test(['c++', '-c', 'src.c']))
        eq(False, test(['clang', '-c', 'src.c']))
        eq(True, test(['clang++', '-c', 'src.c']))
        eq(False, test(['gcc', '-c', 'src.c']))
        eq(True, test(['g++', '-c', 'src.c']))
