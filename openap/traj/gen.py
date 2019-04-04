from openap import aero, prop, Thrust, Drag, FuelFlow, WRAP
import numpy as np

class Generator(object):

    def __init__(self, ac, eng=None):
        super(Generator, self).__init__()

        self.ac = ac
        self.acdict = prop.aircraft(self.ac)

        if eng is None:
            self.eng = self.acdict['engine']['default']
        else:
            self.eng = eng
        self.engdict = prop.engine(self.eng)

        self.wrap = WRAP(self.ac)
        # self.thrust = Thrust(self.ac, self.eng)
        # self.drag = Drag(self.ac)
        # self.fuelflow = Thrust(self.ac, self.eng)

        # for noise generation
        self.sigma_v = 0
        self.sigma_vs = 0
        self.sigma_h = 0
        self.sigma_s = 0

    def enable_noise(self):
        """Adding noise to the generated trajectory
        The noise model is based on ADS-B Version 1&2, NACv=3 and NACp=10
        """
        self.sigma_v = 0.5
        self.sigma_vs = 0.75
        self.sigma_h = 7.5
        self.sigma_s = 5


    def climb(self, **kwargs):
        """Generate climb trajectory based on WRAP model

        Args:
            **dt (int): time step in seconds
            **vcas_const_cl (int): Constaant CAS for climb (m/s)
            **mach_const_cl (float): Constaant Mach for climb (-)
            **h_cr (int): target cruise altitude (m)
            **random (bool): generate trajectory with random vca, mach, alt

        Returns:
            dict: flight trajectory
        """

        dt = kwargs.get('dt', 1)
        random = kwargs.get('random', False)

        a_tof = self.wrap.takeoff_acceleration()['default']
        v_tof = self.wrap.takeoff_speed()['default']

        if random:
            vcas_const = kwargs.get('vcas_const_cl', np.random.uniform(
                self.wrap.climb_const_cas()['minimum'],
                self.wrap.climb_const_cas()['maximum']
            ))

            mach_const = kwargs.get('mach_const_cl', np.random.uniform(
                self.wrap.climb_const_mach()['minimum'],
                self.wrap.climb_const_mach()['maximum']
            ))

            h_cr = kwargs.get('h_cr', np.random.uniform(
                self.wrap.cruise_alt()['minimum'],
                self.wrap.cruise_alt()['maximum']
            ) * 1000)

            vs_pre_constcas = np.random.uniform(
                self.wrap.climb_vs_pre_const_cas()['minimum'],
                self.wrap.climb_vs_pre_const_cas()['maximum']
            )

            vs_constcas = np.random.uniform(
                self.wrap.climb_vs_const_cas()['minimum'],
                self.wrap.climb_vs_const_cas()['maximum']
            )

            vs_constmach = np.random.uniform(
                self.wrap.climb_vs_const_mach()['minimum'],
                self.wrap.climb_vs_const_mach()['maximum']
            )

        else:
            vcas_const = kwargs.get('vcas_const_cl', self.wrap.climb_const_cas()['default'])
            mach_const = kwargs.get('mach_const_cl', self.wrap.climb_const_mach()['default'])
            h_cr = kwargs.get('h_cr', self.wrap.cruise_alt()['default'] * 1000)
            vs_pre_constcas = self.wrap.climb_vs_pre_const_cas()['default']
            vs_constcas = self.wrap.climb_vs_const_cas()['default']
            vs_constmach = self.wrap.climb_vs_const_mach()['default']

        h_cr = np.round(h_cr / aero.ft, -2) * aero.ft   # round cruise altitude to flight level
        vs_ic = self.wrap.initclimb_vs()['default']
        h_const_cas = self.wrap.climb_alt_cross_const_cas()['default'] * 1000

        h_const_mach = aero.crossover_alt(vcas_const, mach_const)
        if h_const_mach > h_cr:
            print('Warining: const mach crossover altitude higher than cruise altitude, altitude clipped.')


        data = []

        # intitial conditions
        t = 0
        tcr = 0
        h = 0
        s = 0
        v = 0
        vs = 0
        a = 0.5   # standard acceleration m/s^2
        seg = None

        while True:
            data.append([t, h, s, v, vs, seg])
            t = t + dt
            s = s + v * dt
            h = h + vs * dt

            if v < v_tof:
                v = v + a_tof * dt
                vs = 0
                seg = 'TO'
            elif h < 1500 * aero.ft:
                v = v + a * dt
                vs = vs_ic
                seg = 'IC'
            elif h < h_const_cas:
                v = v + a * dt
                if aero.tas2cas(v, h) >= vcas_const:
                    v = aero.cas2tas(vcas_const, h)
                vs = vs_pre_constcas
                seg = 'PRE-CAS'
            elif h < h_const_mach:
                v = aero.cas2tas(vcas_const, h)
                vs = vs_constcas
                seg = 'CAS'
            elif h < h_cr:
                v = aero.mach2tas(mach_const, h)
                vs = vs_constmach
                seg = 'MACH'
            else:
                v = aero.mach2tas(mach_const, h)
                vs = 0
                seg = 'CR'
                if tcr == 0:
                    tcr = t
                if t - tcr > 60:
                    break

        data = np.array(data)
        ndata = len(data)
        datadict = {
            't': data[:, 0],
            'h': data[:, 1] + np.random.normal(0, self.sigma_h, ndata),
            's': data[:, 2] + np.random.normal(0, self.sigma_s, ndata),
            'v': data[:, 3] + np.random.normal(0, self.sigma_v, ndata),
            'vs': data[:, 4] + np.random.normal(0, self.sigma_vs, ndata),
            'seg': data[:, 5],
            'vcas_const_cl': vcas_const,
            'mach_const_cl': mach_const,
            'h_cr': h_cr
        }

        return datadict



    def descent(self, **kwargs):
        """Generate descent trajectory based on WRAP model

        Args:
            **dt (int): time step in seconds
            **vcas_const_de (int): Constaant CAS for climb (m/s)
            **mach_const_de (float): Constaant Mach for climb (-)
            **h_cr (int): target cruise altitude (m)
            **random (bool): generate trajectory with random vca, mach, alt

        Returns:
            dict: flight trajectory
        """

        dt = kwargs.get('dt', 1)
        random = kwargs.get('random', False)

        a_lnd = self.wrap.landing_acceleration()['default']
        v_app = self.wrap.finalapp_cas()['default']

        if random:
            h_cr = kwargs.get('h_cr', np.random.uniform(
                self.wrap.cruise_alt()['minimum'],
                self.wrap.cruise_alt()['maximum']
            ) * 1000)

            mach_const = kwargs.get('mach_const_de', np.random.uniform(
                self.wrap.descent_const_mach()['minimum'],
                self.wrap.descent_const_mach()['maximum']
            ))

            vcas_const = kwargs.get('vcas_const_de', np.random.uniform(
                self.wrap.descent_const_cas()['minimum'],
                self.wrap.descent_const_cas()['maximum']
            ))

            vs_constmach = np.random.uniform(
                self.wrap.descent_vs_const_mach()['minimum'],
                self.wrap.descent_vs_const_mach()['maximum']
            )

            vs_constcas = np.random.uniform(
                self.wrap.descent_vs_const_cas()['minimum'],
                self.wrap.descent_vs_const_cas()['maximum']
            )

            vs_post_constcas = np.random.uniform(
                self.wrap.descent_vs_post_const_cas()['minimum'],
                self.wrap.descent_vs_post_const_cas()['maximum']
            )

        else:
            mach_const = kwargs.get('mach_const_de', self.wrap.descent_const_mach()['default'])
            vcas_const = kwargs.get('vcas_const_de', self.wrap.descent_const_cas()['default'])
            h_cr = kwargs.get('h_cr', self.wrap.cruise_alt()['default'] * 1000)
            vs_constmach = self.wrap.descent_vs_const_mach()['default']
            vs_constcas = self.wrap.descent_vs_const_cas()['default']
            vs_post_constcas = self.wrap.descent_vs_post_const_cas()['default']

        h_cr = np.round(h_cr / aero.ft, -2) * aero.ft   # round cruise altitude to flight level
        vs_fa = self.wrap.finalapp_vs()['default']
        h_const_cas = self.wrap.descent_alt_cross_const_cas()['default'] * 1000

        h_const_mach = aero.crossover_alt(vcas_const, mach_const)
        if h_const_mach > h_cr:
            print('Warining: const mach crossover altitude higher than cruise altitude, altitude clipped.')


        data = []

        # intitial conditions
        a = -0.5
        t = 0
        s = 0
        h = h_cr
        v = aero.mach2tas(mach_const, h_cr)
        vs = 0
        seg = None

        while True:
            data.append([t, h, s, v, vs, seg])
            t = t + dt
            s = s + v * dt
            h = h + vs * dt

            if t < 60:
                v = aero.mach2tas(mach_const, h)
                vs = 0
                seg = 'CR'
            elif h > h_const_mach:
                v = aero.mach2tas(mach_const, h)
                vs = vs_constmach
                seg = 'MACH'
            elif h > h_const_cas:
                v = aero.cas2tas(vcas_const, h)
                vs = vs_constcas
                seg = 'CAS'
            elif h > 1000 * aero.ft:
                v = v + a * dt
                if aero.tas2cas(v, h) < v_app:
                    v = aero.cas2tas(v_app, h)
                vs = vs_post_constcas
                seg = 'POST-CAS'
            elif h > 0:
                v = v_app
                vs = vs_fa
                seg = 'FA'
            else:
                h = 0
                vs = 0
                v = v + a_lnd * dt
                seg = 'LD'

                if v <= 0:
                    break


        data = np.array(data)
        ndata = len(data)
        datadict = {
            't': data[:, 0],
            'h': data[:, 1] + np.random.normal(0, self.sigma_h, ndata),
            's': data[:, 2] + np.random.normal(0, self.sigma_s, ndata),
            'v': data[:, 3] + np.random.normal(0, self.sigma_v, ndata),
            'vs': data[:, 4] + np.random.normal(0, self.sigma_vs, ndata),
            'seg': data[:, 5],
            'vcas_const_de': vcas_const,
            'mach_const_de': mach_const,
            'h_cr': h_cr
        }

        return datadict


    def cruise(self, **kwargs):
        """Generate descent trajectory based on WRAP model

        Args:
            **d (int): cruise distance
            **dt (int): time step in seconds
            **vcas (int): Constaant CAS for climb (m/s)
            **mach (float): Constaant Mach for climb (-)
            **alt (int): target cruise altitude (m)
            **random (bool): generate trajectory with random vca, mach, alt

        Returns:
            dict: flight trajectory
        """

        dt = kwargs.get('dt', 1)
        random = kwargs.get('random', False)


        if random:
            d = kwargs.get('d', np.random.uniform(
                self.wrap.cruise_range()['minimum'],
                self.wrap.cruise_range()['maximum']
            ) * 1000)

            h_cr = kwargs.get('h_cr', np.random.uniform(
                self.wrap.cruise_alt()['minimum'],
                self.wrap.cruise_alt()['maximum']
            ) * 1000)

            mach_cr = kwargs.get('mach', np.random.uniform(
                self.wrap.cruise_mach()['minimum'],
                self.wrap.cruise_mach()['maximum']
            ))
        else:
            d = kwargs.get('d', self.wrap.cruise_range()['default'] * 1000)
            mach_cr = kwargs.get('mach', self.wrap.cruise_mach()['default'])
            h_cr = kwargs.get('h_cr', self.wrap.cruise_alt()['default'] * 1000)

        h_cr = np.round(h_cr / aero.ft, -3) * aero.ft   # round cruise altitude to flight level

        data = []

        # intitial conditions
        t = 0
        s = 0
        v = aero.mach2tas(mach_cr, h_cr)
        vs = 0

        while True:
            data.append([t, h_cr, s, v, vs])
            t = t + dt
            s = s + v * dt

            if s > d:
                break

        data = np.array(data)
        ndata = len(data)
        datadict = {
            't': data[:, 0],
            'h': data[:, 1] + np.random.normal(0, self.sigma_h, ndata),
            's': data[:, 2] + np.random.normal(0, self.sigma_s, ndata),
            'v': data[:, 3] + np.random.normal(0, self.sigma_v, ndata),
            'vs': data[:, 4] + np.random.normal(0, self.sigma_vs, ndata),
            'h_cr': h_cr,
            'mach_cr': mach_cr,
        }

        return datadict


    def complete(self, **kwargs):
        """Generate a complete trajectory based on WRAP model

        Args:
            **d (int): cruise distance
            **dt (int): time step in seconds
            **vcas_const_cl (int): Constaant CAS for climb (m/s)
            **mach_const_cl (float): Constaant Mach for climb (-)
            **vcas_const_de (int): Constaant CAS for climb (m/s)
            **mach_const_de (float): Constaant Mach for climb (-)
            **h_cr (int): target cruise altitude (m)
            **random (bool): generate trajectory with random vca, mach, alt
        Returns:
            dict: flight trajectory
        """
        data_cr = self.cruise(**kwargs)
        data_cl = self.climb(alt=data_cr['h_cr'], mach=data_cr['mach_cr'], **kwargs)
        data_de = self.descent(alt=data_cr['h_cr'], mach=data_cr['mach_cr'], **kwargs)

        data = {
            't': np.concatenate([data_cl['t'], data_cl['t'][-1]+data_cr['t'], data_cl['t'][-1]+data_cr['t'][-1]+data_de['t']]),
            'h': np.concatenate([data_cl['h'], data_cr['h'], data_de['h']]),
            's': np.concatenate([data_cl['s'],  data_cl['s'][-1]+data_cr['s'], data_cl['s'][-1]+data_cr['s'][-1]+data_de['s']]),
            'v': np.concatenate([data_cl['v'], data_cr['v'], data_de['v']]),
            'vs': np.concatenate([data_cl['vs'], data_cr['vs'], data_de['vs']]),
        }
        return data