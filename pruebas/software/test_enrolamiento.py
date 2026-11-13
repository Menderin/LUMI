import unittest
from software.percepcion.enrolamiento.estado import Enrolamiento


class Estados(unittest.TestCase):
    def test_exito_y_rearme(self):
        s = Enrolamiento(minimo=2)
        self.assertFalse(s.actualizar(0, pulsacion=True))
        self.assertEqual(s.leds(0), (False, False, True))
        s.actualizar(1, personas=1, recorte=[1])
        s.actualizar(2, personas=1, recorte=[2])
        self.assertFalse(s.actualizar(10, cobertura=True, objetivo=True))
        self.assertEqual(s.galeria, ([1], [2]))
        self.assertEqual([s.leds(10+i/4)[0] for i in range(7)],
                         [True, False, True, False, True, False, False])
        self.assertTrue(s.actualizar(12, pulsacion=True, objetivo=True))
        self.assertFalse(s.actualizar(13))
        self.assertEqual(s.leds(13), (False, True, False))
        self.assertFalse(s.actualizar(14, objetivo=True))
        self.assertTrue(s.actualizar(15, pulsacion=True, objetivo=True))

    def test_fallo_y_limite(self):
        s = Enrolamiento(minimo=1)
        for t in range(0, 60, 12):
            s.actualizar(t, pulsacion=True)
            s.actualizar(t+1, personas=2, recorte=[1])
            self.assertFalse(s.actualizar(t+10, cobertura=True))
            self.assertEqual(s.estado, "fallo")
            self.assertEqual(s.leds(t+10), (False, False, True))
            self.assertEqual(s.leds(t+10.25), (False, False, False))
        s.actualizar(60, pulsacion=True)
        self.assertEqual(s.intentos, 5)
        self.assertEqual(s.estado, "fallo")

