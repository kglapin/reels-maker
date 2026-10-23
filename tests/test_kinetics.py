"""Reference animation regression from user-supplied reels11.py."""
import unittest
from reels_maker.kinetics import (
    counter_value, format_pln, animated_crop, progress,
    ease_out_cubic, settle_back
)


class KineticTests(unittest.TestCase):
    def test_counter_respects_audio_cue_and_lands_on_amount(self):
        sequence = [counter_value(16000, i, 8, 30) for i in range(60)]
        self.assertEqual(sequence[:9], [0]*9)
        self.assertEqual(sequence[38:], [16000]*22)
        self.assertEqual(sequence, sorted(sequence))
        self.assertEqual(format_pln(sequence[-1]), "16 000 zł")

    def test_counter_supports_percentage_and_decrement(self):
        self.assertEqual(counter_value(30, 50, 20, 15), 30)
        self.assertEqual(counter_value(0, 30, 0, 30, start=100), 0)
        self.assertEqual(counter_value(100, 0, 10, 20, start=40), 40)

    def test_easing_is_bounded_and_monotone(self):
        values = [ease_out_cubic(i/100) for i in range(101)]
        self.assertEqual(values[0], 0)
        self.assertEqual(values[-1], 1)
        self.assertEqual(values, sorted(values))
        self.assertAlmostEqual(settle_back(1), 1)
        with self.assertRaises(ValueError):
            settle_back(0.3, 1.5)

    def test_crop_interpolation_holds_start_and_end(self):
        start=(1.05,0.48,0.48)
        end=(1.25,0.62,0.52)
        self.assertEqual(animated_crop(start,end,0,10,45),start)
        self.assertEqual(animated_crop(start,end,55,10,45),end)
        mid=animated_crop(start,end,30,10,45)
        self.assertTrue(all(min(a,b)<=x<=max(a,b)
                            for a,b,x in zip(start,end,mid)))

    def test_invalid_inputs_fail_loudly(self):
        for args in ((5,-1,0,10),(5,1,-1,10),(5,1,0,0)):
            with self.assertRaises(ValueError):
                counter_value(*args)
        with self.assertRaises(ValueError):
            animated_crop((1,0,0),(0,1,1),0,0,10)
        with self.assertRaises(ValueError):
            ease_out_cubic(float("nan"))


if __name__=="__main__":
    unittest.main()
