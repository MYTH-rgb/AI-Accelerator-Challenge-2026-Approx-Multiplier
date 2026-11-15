`timescale 1ns / 1ps
module hwmaj_ilp6t_asic (
    input  wire signed [7:0]  a,
    input  wire signed [7:0]  b,
    output wire signed [15:0] p
);
    wire [7:0] ua = a;
    wire [7:0] ub = b;


    wire [1:0] ma = ((ua[0]&ua[1])|(ua[0]&ua[2])|(ua[1]&ua[2])) + ((ua[3]&ua[4])|(ua[3]&ua[5])|(ua[4]&ua[5]));
    wire [1:0] mb = ((ub[0]&ub[1])|(ub[0]&ub[2])|(ub[1]&ub[2])) + ((ub[3]&ub[4])|(ub[3]&ub[5])|(ub[4]&ub[5]));
    wire nz = (|ua[5:0]) & (|ub[5:0]);
    reg [2:0] g;
    always @* begin
        case ({nz,ma,mb})
            5'd0: g = 3'd0;
            5'd16: g = 3'd0;
            5'd17: g = 3'd0;
            5'd18: g = 3'd0;
            5'd20: g = 3'd0;
            5'd21: g = 3'd1;
            5'd22: g = 3'd1;
            5'd24: g = 3'd0;
            5'd25: g = 3'd1;
            5'd26: g = 3'd2;
            default: g = 3'd0;
        endcase
    end
    wire [8:0] comp = {g, nz ? 6'd40 : 6'd0};

    wire pp_0_6_6 = (ua[0] & ub[6]);
    wire pp_1_5_6 = (ua[1] & ub[5]);
    wire pp_2_4_6 = (ua[2] & ub[4]);
    wire pp_3_3_6 = (ua[3] & ub[3]);
    wire pp_4_2_6 = (ua[4] & ub[2]);
    wire pp_5_1_6 = (ua[5] & ub[1]);
    wire pp_6_0_6 = (ua[6] & ub[0]);
    wire pp_0_7_7 = ~(ua[0] & ub[7]);
    wire pp_1_6_7 = (ua[1] & ub[6]);
    wire pp_2_5_7 = (ua[2] & ub[5]);
    wire pp_3_4_7 = (ua[3] & ub[4]);
    wire pp_4_3_7 = (ua[4] & ub[3]);
    wire pp_5_2_7 = (ua[5] & ub[2]);
    wire pp_6_1_7 = (ua[6] & ub[1]);
    wire pp_7_0_7 = ~(ua[7] & ub[0]);
    wire pp_1_7_8 = ~(ua[1] & ub[7]);
    wire pp_2_6_8 = (ua[2] & ub[6]);
    wire pp_3_5_8 = (ua[3] & ub[5]);
    wire pp_4_4_8 = (ua[4] & ub[4]);
    wire pp_5_3_8 = (ua[5] & ub[3]);
    wire pp_6_2_8 = (ua[6] & ub[2]);
    wire pp_7_1_8 = ~(ua[7] & ub[1]);
    wire pp_2_7_9 = ~(ua[2] & ub[7]);
    wire pp_3_6_9 = (ua[3] & ub[6]);
    wire pp_4_5_9 = (ua[4] & ub[5]);
    wire pp_5_4_9 = (ua[5] & ub[4]);
    wire pp_6_3_9 = (ua[6] & ub[3]);
    wire pp_7_2_9 = ~(ua[7] & ub[2]);
    wire pp_3_7_10 = ~(ua[3] & ub[7]);
    wire pp_4_6_10 = (ua[4] & ub[6]);
    wire pp_5_5_10 = (ua[5] & ub[5]);
    wire pp_6_4_10 = (ua[6] & ub[4]);
    wire pp_7_3_10 = ~(ua[7] & ub[3]);
    wire pp_4_7_11 = ~(ua[4] & ub[7]);
    wire pp_5_6_11 = (ua[5] & ub[6]);
    wire pp_6_5_11 = (ua[6] & ub[5]);
    wire pp_7_4_11 = ~(ua[7] & ub[4]);
    wire pp_5_7_12 = ~(ua[5] & ub[7]);
    wire pp_6_6_12 = (ua[6] & ub[6]);
    wire pp_7_5_12 = ~(ua[7] & ub[5]);
    wire pp_6_7_13 = ~(ua[6] & ub[7]);
    wire pp_7_6_13 = ~(ua[7] & ub[6]);
    wire pp_7_7_14 = (ua[7] & ub[7]);
    wire s1 = pp_0_7_7 ^ pp_1_6_7 ^ pp_2_5_7;
    wire k1 = (pp_0_7_7 & pp_1_6_7) | (pp_2_5_7 & (pp_0_7_7 ^ pp_1_6_7));
    wire s2 = pp_3_4_7 ^ pp_4_3_7 ^ pp_5_2_7;
    wire k2 = (pp_3_4_7 & pp_4_3_7) | (pp_5_2_7 & (pp_3_4_7 ^ pp_4_3_7));
    wire s3 = 1'b1 ^ pp_1_7_8 ^ pp_2_6_8;
    wire k3 = (1'b1 & pp_1_7_8) | (pp_2_6_8 & (1'b1 ^ pp_1_7_8));
    wire s4 = pp_3_7_10 ^ pp_4_6_10 ^ pp_5_5_10;
    wire k4 = (pp_3_7_10 & pp_4_6_10) | (pp_5_5_10 & (pp_3_7_10 ^ pp_4_6_10));
    wire s5 = pp_4_7_11 ^ pp_5_6_11 ^ pp_6_5_11;
    wire k5 = (pp_4_7_11 & pp_5_6_11) | (pp_6_5_11 & (pp_4_7_11 ^ pp_5_6_11));
    wire s6 = pp_5_7_12 ^ pp_6_6_12 ^ pp_7_5_12;
    wire k6 = (pp_5_7_12 & pp_6_6_12) | (pp_7_5_12 & (pp_5_7_12 ^ pp_6_6_12));
    wire s7 = pp_0_6_6 ^ pp_1_5_6 ^ pp_2_4_6;
    wire k7 = (pp_0_6_6 & pp_1_5_6) | (pp_2_4_6 & (pp_0_6_6 ^ pp_1_5_6));
    wire s8 = pp_3_5_8 ^ pp_4_4_8 ^ pp_5_3_8;
    wire k8 = (pp_3_5_8 & pp_4_4_8) | (pp_5_3_8 & (pp_3_5_8 ^ pp_4_4_8));
    wire s9 = pp_6_2_8 ^ pp_7_1_8 ^ k1;
    wire k9 = (pp_6_2_8 & pp_7_1_8) | (k1 & (pp_6_2_8 ^ pp_7_1_8));
    wire s10 = k2 ^ s3 ^ comp[8];
    wire k10 = (k2 & s3) | (comp[8] & (k2 ^ s3));
    wire s11 = pp_2_7_9 ^ pp_3_6_9 ^ pp_4_5_9;
    wire k11 = (pp_2_7_9 & pp_3_6_9) | (pp_4_5_9 & (pp_2_7_9 ^ pp_3_6_9));
    wire s12 = pp_5_4_9 ^ pp_6_3_9 ^ pp_7_2_9;
    wire k12 = (pp_5_4_9 & pp_6_3_9) | (pp_7_2_9 & (pp_5_4_9 ^ pp_6_3_9));
    wire s13 = pp_6_4_10 ^ pp_7_3_10 ^ s4;
    wire k13 = (pp_6_4_10 & pp_7_3_10) | (s4 & (pp_6_4_10 ^ pp_7_3_10));
    wire s14 = pp_7_4_11 ^ k4 ^ s5;
    wire k14 = (pp_7_4_11 & k4) | (s5 & (pp_7_4_11 ^ k4));
    wire s15 = pp_6_7_13 ^ pp_7_6_13 ^ k6;
    wire k15 = (pp_6_7_13 & pp_7_6_13) | (k6 & (pp_6_7_13 ^ pp_7_6_13));
    wire s16 = s8 ^ s9 ^ s10;
    wire k16 = (s8 & s9) | (s10 & (s8 ^ s9));
    wire s17 = k3 ^ k8 ^ s11;
    wire k17 = (k3 & k8) | (s11 & (k3 ^ k8));
    wire s18 = s12 ^ k9 ^ k10;
    wire k18 = (s12 & k9) | (k10 & (s12 ^ k9));
    wire s19 = k11 ^ k12 ^ s13;
    wire k19 = (k11 & k12) | (s13 & (k11 ^ k12));
    wire s20 = pp_6_1_7 ^ pp_7_0_7 ^ s1;
    wire k20 = (pp_6_1_7 & pp_7_0_7) | (s1 & (pp_6_1_7 ^ pp_7_0_7));
    wire s21 = s2 ^ k7 ^ comp[7];
    wire k21 = (s2 & k7) | (comp[7] & (s2 ^ k7));
    wire s22 = s17 ^ k16 ^ s18;
    wire k22 = (s17 & k16) | (s18 & (s17 ^ k16));
    wire s23 = k13 ^ s14 ^ k19;
    wire k23 = (k13 & s14) | (k19 & (k13 ^ s14));
    wire s24 = pp_3_3_6 ^ pp_4_2_6 ^ pp_5_1_6;
    wire k24 = (pp_3_3_6 & pp_4_2_6) | (pp_5_1_6 & (pp_3_3_6 ^ pp_4_2_6));
    wire s25 = pp_6_0_6 ^ s7 ^ comp[6];
    wire k25 = (pp_6_0_6 & s7) | (comp[6] & (pp_6_0_6 ^ s7));
    wire s26 = k20 ^ k21 ^ s16;
    wire k26 = (k20 & k21) | (s16 & (k20 ^ k21));
    wire s27 = k24 ^ s20 ^ s21;
    wire k27 = (k24 & s20) | (s21 & (k24 ^ s20));
    wire s28 = k17 ^ s19 ^ k18;
    wire k28 = (k17 & s19) | (k18 & (k17 ^ s19));
    wire s29 = k5 ^ s6 ^ k14;
    wire k29 = (k5 & s6) | (k14 & (k5 ^ s6));
    wire [15:0] v1 = {1'b1, pp_7_7_14, s15, k23, s23, k22, k26, s26, k25, s24, comp[5], 1'b0, comp[3], 1'b0, 1'b0, 1'b0};
    wire [15:0] v2 = {1'b0, k15, k29, s29, k28, s28, s22, k27, s27, s25, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
    assign p = v1 + v2;
endmodule
