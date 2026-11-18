import unittest
from datetime import datetime,timedelta,timezone
from comparison import comparison
class Boundaries(unittest.TestCase):
 def setUp(self): self.t=datetime(2020,1,1)
 def check(self,old,new,hours,a,r):
  x=comparison(self.t,old,self.t+timedelta(hours=hours),new)
  self.assertEqual((x['absolute_48h'],x['ratio_7d']),(a,r))
  self.assertEqual(x['gates'],{'CLINICAL_ACCEPTANCE':'HOLD','AKI_ENDPOINT_READY':False,'ML_TRAINING_PERMITTED':False})
 def test_absolute_exact(self): self.check('1','1.3',48,True,False)
 def test_absolute_below(self): self.check('1','1.299999',48,False,False)
 def test_absolute_expired(self): self.check('1','1.3',48+1/3600,False,False)
 def test_ratio_exact(self): self.check('1','1.5',168,False,True)
 def test_ratio_below(self): self.check('1','1.499999',168,False,False)
 def test_ratio_expired(self): self.check('1','1.5',168+1/3600,False,False)
 def test_both(self): self.check('1','1.5',24,True,True)
 def test_falling(self): self.check('2','1',24,False,False)
 def test_no_absolute_from_old_nadir(self): self.check('2','2.3',100,False,False)
 def test_same_time_and_future(self):
  for h in [0,-1]: self.assertEqual(comparison(self.t,1,self.t+timedelta(hours=h),2)['status'],'NOT_EVALUABLE')
 def test_bad_values(self):
  for v in [None,'',0,-1,'NaN','Infinity','bad']:
   self.assertEqual(comparison(self.t,v,self.t+timedelta(hours=1),2)['status'],'NOT_EVALUABLE')
 def test_units(self): self.assertEqual(comparison(self.t,88.4,self.t+timedelta(hours=1),120,'umol/L')['status'],'NOT_EVALUABLE')
 def test_timezone_mismatch(self): self.assertEqual(comparison(self.t,1,self.t.replace(tzinfo=timezone.utc),2)['reason'],'INCONSISTENT_TIMEZONE')
 def test_missing_time(self): self.assertEqual(comparison(None,1,self.t,2)['status'],'NOT_EVALUABLE')
if __name__=='__main__':unittest.main()
