#include "MyBQ25798.h"

void MyBQ25798::init()
{
  while (!bq25798.begin()) {
    delay(100);
  }
  bq25798.clearError();

  // Reset the chip and wait for it to finish:
  bq25798.setREG_RST(true);
  while (bq25798.getREG_RST()) {
    delay(10);
  }
}