# This is not a real gradient descent algorithm; it's just for testing purpose. This is from my old code.

def tune(self, max_samples, variables_count):
        # These could be best values we got till now (Current numbers or start from something like 50.0).
        old_values = []
        for i in range(variables_count):
            old_values.append(0)
        old_values[0] = 50
        old_values[1] = 50
        old_values[2] = 50
        old_values[3] = 50
        old_values[4] = 50
        old_values[5] = 50

        values = []
        delta_values = []
        for i in range(variables_count):
            values.append(0.0)
            old_values[i] *= 1.0   # for performance!
            values[i] = old_values[i]
            delta_values.append(0.0)

        p = open('result.txt', 'a+')
        p.writelines('\n------------New session started-----------------\n')
        delta_error = 0.0
        for i in range(variables_count):
            self.modified_engine.setoption({('vAlUe' + i.__repr__()): old_values[i]})
        self.modified_engine.ucinewgame(async_callback=False)
        min_error = error = self.mse(max_samples)
        p.writelines('error: ' + error.__repr__() + '\n---------------------------------------\n')
        print('error: ' + error.__repr__())
        for epoch in range(10000):
            p.write('Epoch:' + epoch.__repr__() + '\n')
            print('Epoch:' + epoch.__repr__())
            p.write('Values:\n')
            # update values
            for i in range(variables_count):
                old_values[i] = values[i]
                if epoch == 0 or delta_error == 0.0:    # or error == min_error:
                    values[i] += + 2.0 * (random.random() - 0.5) * 20.0
                elif delta_error > 0.0:
                    values[i] -= delta_values[i] * 0.7
                else:
                    values[i] += delta_values[i] * 0.7
                # or you can use error instead of 10
                if values[i] < 0.0:
                    values[i] = 0.0
                if values[i] > 1000.0:
                    values[i] = 1000.0
                delta_values[i] = values[i] - old_values[i]
                new_value = round(values[i])
                value_name = 'vAlUe' + i.__repr__()
                self.modified_engine.setoption({value_name: new_value})
                p.writelines('old_values[' + i.__repr__() + '] = ' + new_value.__repr__() + '\n')
            self.modified_engine.ucinewgame(async_callback=False)
            old_error = error
            error = self.mse(max_samples)
            delta_error = error - old_error
            p.writelines('error: ')
            print('error: ')
            print(error)
            if error < min_error:
                for i in range(variables_count):
                    old_values[i] = values[i]
                min_error = error
                p.writelines('Found better values!\n')
                print('Found better values!')
            p.writelines(error.__repr__() + '\n---------------------------------------\n')
            print('--------------------------------------------------')
            if error == 0:
                print('Congrats!')
                break
        p.close()
