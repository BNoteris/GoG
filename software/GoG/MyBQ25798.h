#ifndef MYBQ25798_H
#define MYBQ25798_H

#include <BQ25798.h>


class MyBQ25798
{
public:
    MyBQ25798();

    void init();


private:
    BQ25798 bq25798;
};

#endif // MYBQ25798_H