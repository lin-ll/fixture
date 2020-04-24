

/****************************************************************
* This code is automatically generated by "mGenero"
* at Wed, 25 Mar 2020 14:34:55.
*
* Copyright (c) 2014-Present by Stanford University. All rights reserved.
*
* The information and source code contained herein is the property
* of Stanford University, and may not be disclosed or reproduced
* in whole or in part without explicit written authorization from
* Stanford University.
* For more information, contact bclim@stanford.edu
****************************************************************/
/****************************************************************

Copyright (c) 2018 Stanford University. All rights reserved.

The information and source code contained herein is the 
property of Stanford University, and may not be disclosed or
reproduced in whole or in part without explicit written 
authorization from Stanford University.

* Filename   : amplifier.template.sv
* Author     : Byongchan Lim (bclim@stanford.edu)
* Description: SV template for an amplifier cell

* Note       :

* Todo       :
  - 

* Revision   :
  - 00/00/00 : 

****************************************************************/
/*******************************************************
* An amplifier with possible output equalization
* - Input referred voltage offset as a static parameter
* - Gain Compression
* - Dynamic behavior (a pole or two-poles with a zero)
* - 

* Calibrating metrics:
* 1. Av = gm*Rout 
* 2. Max output swing = Itail*Rout 
* 3. fp1, fp2, fz1
*******************************************************/

`include "mLingua_pwl.vh"

module myphaseblender #(
  parameter real max_delay = 2e6 // Maximum time allowed between output edges
) (
  input logic  input_a, // input_a
  input logic  input_b, // input_b
  output logic  output_, // output_
  input logic [2:0] sel, // sel
  input real  gnd, // gnd
  input real  vdd // vdd
);

`protect
//pragma protect 
//pragma protect begin

`get_timeunit
PWLMethod pm=new;

// about to map
// map pins between generic names and user names, if they are different
logic  in_a;
logic  in_b;
logic  out;
assign in_a = input_a ;
assign in_b = input_b ;
assign output_ = out ; // just mapped

//----- BODY STARTS HERE -----

//----- SIGNAL DECLARATION -----
pwl ONE = `PWL1;
pwl ZERO = `PWL0;

// pwl v_id_lim;   // limited v_id 
// pwl v_oc; // output common-mode voltage
// pwl v_od; // output differential voltage
// pwl vid_max, vid_min; // max/min of v_id for slewing 
// pwl vop, von;
// pwl v_od_filtered;
// pwl vop_lim, von_lim;
// pwl v_id, v_icm; // differential and common-mode inputs

// TODO is t0 ever used? does mLingua need it?
real t0;
// real v_icm_r;
// real vdd_r;

// real fz1, fp1, fp2; // at most, two poles and a zero
// real Av;    // voltage gain (gm*Rout)
// real max_swing; // Max voltage swing of an output (Itail*Rout)
// real vid_r; // vid<|vid_r| (max_swing/Av)
// real v_oc_r;  // common-mode output voltage

// Declaration of params
real gain;
real offset;

event wakeup;

//----- FUNCTIONAL DESCRIPTION -----

initial ->> wakeup; // dummy event for ignition at t=0

//-- System's parameter calculation

// discretization of control inputs

// updating parameters as control inputs/mode inputs change

always @(wakeup, sel, vdd, gnd) begin
  t0 = `get_time;

// TODO do I need to annotate modelparam?

  gain = -0.470178408166*sel[0]*1-0.823167394677*sel[2]*1-1.07355983239*sel[1]*1;
  offset = 0.460757524873*1;

end

//-- Model behaviors

event set_high;
event set_low;
real period_unclamped;
real period;
real rising_a;
real diff;
real delay_periods;
real delay_unshifted;
//real delay_unclamped;
real delay;
real wait_unshifted;
real w;

always @(posedge(in_a)) begin
    period_unclamped = `get_time - rising_a;
    period = period_unclamped > max_delay? max_delay : period_unclamped;
    rising_a = `get_time;
end

always @(posedge(in_b)) begin
    diff = `get_time - rising_a;
    delay_periods = diff / period * gain + offset + 1;
    delay_unshifted = delay_periods * period;
    delay = delay_unshifted <  0?      delay_unshifted + period
          : delay_unshifted >= period? delay_unshifted - period
          : delay_unshifted;
    // delay is now the time from rising edge of a to rising edge of out
end

initial begin
    wait(in_a == 0);
    wait(in_b == 0);
    wait(in_a == 1);
    wait(in_b == 1);
    ->> set_high;
end

always @(set_high) begin
    out = 1;
    #(period / 2 *1s) ->> set_low;
end
always @(set_low) begin
    out = 0;
    // now we schedule the next high edge
    // t = prev_a + delay
    // wait = t - current_time
    wait_unshifted = rising_a + delay - `get_time;
    // value is usually almost exactly period/2, we will clamp 0 <= w < period
    // TODO this might be redundant with shifting we already did to delay
    w = wait_unshifted < 0?       wait_unshifted + period
      : wait_unshifted >= period? wait_unshifted - period
      : wait_unshifted;
    #(w * 1s) ->> set_high;
end

//pragma protect end
`endprotect

endmodule