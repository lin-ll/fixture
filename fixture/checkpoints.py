import csv
import os

import magma
import fault
import jsonpickle
import re

import pandas

import fixture









# TODO delete this one, it's unused!
class Checkpoint:

    def __init__(self):
        self.circuits_data = []

    def create_circuit(self, name_, io):
        # this is broken into its own method because of the way it will be
        # saved in jsonpickle as a class belonging to this method's locals
        # The root issue for this confusion is that magma circuits are classes,
        # and jsonpickle doesn't save classes
        # We also save the inputs so we can re-create this
        self.circuits_data.append((name_, io))

        class UserCircuit(magma.Circuit):
            name = name_
            IO = io

        return UserCircuit

    def save(self, thing, filename):
        # because jsonpickle will not store classes we have to save magma
        # circuits separately, and then restore them first and provide them
        # when we restore the rest
        combined = {}
        p1 = jsonpickle.Pickler(keys=True, warn=True)
        circuits_dict = p1.flatten(self.circuits_data)
        p2 = jsonpickle.Pickler(keys=True, warn=True)
        thing_dict = p2.flatten(thing)

        debug_pickling = True
        if debug_pickling:
            # if the unpickler doesn't have the right classes in scope it will
            # fail to unpickle some things, and then there's a mismatch between
            # the pickling and unpickling object lists, and this is a
            # way to take a look at the pickling object list
            obj_ids = p2._objs
            import gc
            all_objs = gc.get_objects()
            all_objs_map = {id(obj): obj for obj in all_objs}
            # I think UNKNOWN ones were garbage collected during pickling?
            objs = [all_objs_map[id_] if id_ in all_objs_map else 'UNKNOWN'
                    for id_ in obj_ids]
            for i, obj in enumerate(objs):
                print(f'{i} : {type(obj)} : {obj}')

        combined = [circuits_dict, thing_dict]
        s = jsonpickle.json.encode(combined, indent=2)
        with open(filename, 'w') as f:
            f.write(s)

    @staticmethod
    def get_type(type_string):
        # I used to build the result using the module path at the beginning of
        # type_string, but it turns out we will need to hard-code those paths
        # here anyway because they will be missing when a type is wrapped in
        # a magma.array
        # e.g. 'magma.array.Array[(2, Out(RealType))]' hides the fact that
        # RealType comes from fault.ms_types, so there's no point in trying
        # to parse out fault.ms_types from 'fault.ms_types.RealType[In]'

        def aux(s):
            # explicit types
            if s == 'RealType':
                return fault.ms_types.RealType
            if s == 'Bit':
                return magma.Bit

            # magma In
            m = re.match('(.*?)\\[In\\]$', s)
            if m:
                return magma.In(aux(m.group(1)))
            m = re.match('In\\((.*?)\\)$', s)
            if m:
                return magma.In(aux(m.group(1)))

            # magma Out
            m = re.match('(.*?)\\[Out\\]$', s)
            if m:
                return magma.Out(aux(m.group(1)))
            m = re.match('Out\\((.*?)\\)$', s)
            if m:
                return magma.Out(aux(m.group(1)))

            # magma Array
            m = re.match('Array\\[\\(?(\\d+), (.*?)\\)?\\]$', s)
            if m:
                return magma.Array[int(m.group(1)), aux(m.group(2))]

            assert False, f'Could not recognize type string: {s}'

        s = type_string.split('.')[-1]
        t = aux(s)
        return t

    @staticmethod
    def related_types(pin):
        yield magma.In(pin)
        yield magma.Out(pin)
        if isinstance(pin, magma.ArrayMeta):
            for x in Checkpoint.related_types(pin.T):
                yield x

    def load(self, filename):
        with open(filename) as f:
            s = f.read()
            combined = jsonpickle.json.decode(s)
            circuits_dict, thing_dict = combined

            # first we re-create the magma io types
            # this is a bit hacky and depends on the structure of circuits_dict
            ios = [cd['py/tuple'][1] for cd in circuits_dict]
            type_strings = [x['py/type']
                            for io in ios for x in io if isinstance(x, dict)]

            io_types = [self.get_type(s) for s in type_strings]
            # because fixture Signals have references to individual bits in a
            # magma bus, we need to provide those to the Unpickler too
            # also for some reason In and Out get flipped sometimes, so we
            # just provide both versions of everything
            io_types_all = {x for t in io_types
                            for x in self.related_types(t)}
            io_types_all = list(io_types_all)

            # now that we have the io types, re-create the user circuit
            p1 = jsonpickle.Unpickler(keys=True)
            circuits_data = p1.restore(circuits_dict, classes=io_types_all)
            circuits = [self.create_circuit(*cd) for cd in circuits_data]

            # now use the io types and user circuit to do the rest
            classes = circuits + io_types_all
            p2 = jsonpickle.Unpickler(keys=True)
            thing = p2.restore(thing_dict, classes=classes)

            return thing


class MyTest:
    pass




@jsonpickle.handlers.register(magma.DefineCircuitKind)#type(magma.Bit))
class MagmaCircuitHandler(jsonpickle.handlers.BaseHandler):
    def flatten(self, obj, data):
        print('in flatten', obj)
        pass

    def restore(self, obj):
        pass

def temp_getstate():
    print('in getstate')
    return {'test': 'getstate'}


if __name__ == '__main__':
    with open('pickletest2.json') as f:
        s = f.read()

    #class UserCircuit:
    #    name = 'bad_test'
    #    IO = ['bad_in', magma.In(magma.Bit)]

    fake_io = ['fake_in', magma.In(magma.Bit),
               'fake_out', magma.Out(magma.Bit),
               'fake_vdd', magma.In(fault.ms_types.RealType),
               'fake_vss', magma.In(fault.ms_types.RealType)
               ]
    x = fixture.config_parse.create_circuit('fake_name', fake_io)
    #x.UserCircuit = UserCircuit


    useful_type1 = magma.In(fault.ms_types.RealType)
    useful_type2 = type(x.fake_vdd)
    t = jsonpickle.decode(s, keys=True, classes=[x, useful_type1, useful_type2])

    exit()
    MyTest.important = 'Hi!'

    class MyCircuit(magma.Circuit):
        name = 'test'
        IO = ['input', magma.In(magma.Bit)]

    MyCircuit.__getstate__ = temp_getstate


    print(isinstance(MyCircuit, magma.DefineCircuitKind))
    x = [5, 'hi', (1,2,3), MyCircuit, 'x']
    s = jsonpickle.encode(x)
    print(s)



# This is the real one!
class Checkpoint:
    def __init__(self, template, filepath):
        self.template = template
        self.filepath = filepath
        self.data = {}
        for test in self.template.tests:
            test_data = {
                'input_vectors': None,
                'sim_result_folder': None,
                'extracted_data': None,
                'regression_results': None
            }
            self.data[test] = test_data

    def convert_df_columns(self, test, df):
        str_to_signal = {str(s): s for s in test.signals.flat()}
        test = df.rename(str_to_signal, axis='columns', inplace=True)
        print(test)

    def _get_save_file(self, test, filename):
        # DON'T FORGET TO CLOSE IT
        folder = os.path.join(self.filepath, str(test))
        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(folder, filename)
        if os.path.exists(filename):
            print(f'Overwriting file {filename}')

        f = open(filename, 'w')
        return f

    def _get_load_file(self, test, filename):
        # DON'T FORGET TO CLOSE IT
        folder = os.path.join(self.filepath, str(test))
        filename = os.path.join(folder, filename)
        f = open(filename, 'r')
        return f


    def save_input_vectors(self, test, input_vectors):
        self.data[test]['input_vectors'] = input_vectors
        f = self._get_save_file(test, 'input_vectors.csv')
        writer = csv.writer(f)
        keys = list(input_vectors.keys())
        writer.writerow([str(key) for key in keys])
        column_major = [input_vectors[key] for key in keys]
        row_major = zip(*column_major)
        writer.writerows(row_major)
        f.close()

    def load_input_vectors(self, test):
        if True or self.data[test]['input_vectors'] is None:
            f = self._get_load_file(test, 'input_vectors.csv')
            #reader = csv.reader(f)
            #headers = reader.__next__()
            #str_to_signal = {str(s): s for s in test.signals.flat()}
            ## TODO do we also need the non-flat versions of the buses?
            #keys = [str_to_signal[h] for h in headers]
            #column_major = zip(*reader)
            #f.close()
            #input_vectors = {key: values
            #                 for key, values in zip(keys, column_major)}
            input_vectors = pandas.read_csv(f)
            self.convert_df_columns(test, input_vectors)
            f.close()
            self.data[test]['input_vectors'] = input_vectors

        iv = self.data[test]['input_vectors']
        return iv


    def suggest_run_dir(self, test):
        return os.path.join(self.filepath, str(test))

    def save_run_dir(self, test, run_dir):
        self.data[test]['sim_result_folder'] = run_dir

    def save_extracted_data(self, test, data):
        self.data[test]['extracted_data'] = data
        f = self._get_save_file(test, 'extracted_data.csv')
        data.to_csv(f)
        f.close()

    def load_extracted_data(self, test):
        if True or self.data[test]['input_vectors'] is None:
            f = self._get_load_file(test, 'extracted_data.csv')
            data = pandas.read_csv(f)
            self.convert_df_columns(test, data)
            self.data[test]['extracted_data'] = data
            f.close()

        data = self.data[test]['extracted_data']
        return data



