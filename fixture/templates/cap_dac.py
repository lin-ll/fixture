from fixture import TemplateMaster
import itertools
from fixture.template_creation_utils import debug

class CapDACTemplate(TemplateMaster):
    required_ports = ['sample_in', 'ctrl_in', 'clk', 'out']

    @debug
    class Test1(TemplateMaster.Test):
        parameter_algebra = {
            'out': {'gain_in': 'sample_in*ctrl_in', 'gain': 'ctrl_in',
                    'offset_in': 'sample_in', 'offset': '1'},
        }
        required_info = {
            'approx_settling_time': 'Approximate time it takes for amp to settle within 99% (s)'
        }

        def input_domain(self):
            ctrl_in = self.signals.from_template_name('ctrl_in')
            sample_in = self.signals.sample_in
            return [*ctrl_in, sample_in]

        def testbench(self, tester, values):
            wait_time = self.extras['approx_settling_time'] * 2

            self.debug(tester, self.ports.ctrl_in[0], 1)
            self.debug(tester, self.ports.ctrl_in[1], 1)
            self.debug(tester, self.ports.clk, 1)
            self.debug(tester, self.ports.sample_in, 1)
            self.debug(tester, self.ports.out, 1)

            # reset bits
            for bit in self.ports.ctrl_in:
                tester.poke(bit, 0)

            # sample input
            tester.poke(self.ports.sample_in, values['sample_in'])
            tester.poke(self.ports.clk, 1)
            tester.delay(wait_time)
            tester.poke(self.ports.clk, 0)

            # flip appropriate bits
            for bit in self.signals.ctrl_in:
                tester.poke(bit.spice_pin, values[bit])

            # read
            tester.delay(wait_time)
            read = tester.get_value(self.ports.out)

            return read

        def analysis(self, reads):
            results = {'out': reads.value}
            return results

    @debug
    class INLTest(TemplateMaster.Test):
        num_samples = 1
        def __init__(self, *args, **kwargs):
            template = args[0]

            in_ = template.signals.in_

            self.parameter_algebra = {}
            self.N = len(in_)
            self.words = list(itertools.product(range(2), repeat=self.N))
            self.word_names = []

            bit_order_name = '_'.join(s.spice_name for s in in_)
            for word in self.words:
                word_name = '_'.join(str(i) for i in word)
                name = bit_order_name + '__' + word_name
                self.word_names.append(name)
                self.parameter_algebra[name] = {f'{name}_meas': '1'}

            super().__init__(*args, **kwargs)

        def input_domain(self):
            return []

        def testbench(self, tester, values):
            for i in range(self.N):
                self.debug(tester, self.ports.in_[i], 1)
            self.debug(tester, self.ports.outp, 1)
            self.debug(tester, self.ports.outn, 1)

            wait_time = self.extras['approx_settling_time'] * 2

            reads = []
            for word in self.words:
                for bit, val in zip(self.signals.in_, word):
                    tester.poke(bit.spice_pin, val)

                tester.delay(wait_time)
                outp = tester.get_value(self.ports.outp)
                outn = tester.get_value(self.ports.outn)
                reads.append((outp, outn))
            return reads

        def analysis(self, reads):
            results = {}

            for word_name, read in zip(self.word_names, reads):
                results[word_name] = read[1].value - read[0].value

            return results


    tests = [Test1]

    

