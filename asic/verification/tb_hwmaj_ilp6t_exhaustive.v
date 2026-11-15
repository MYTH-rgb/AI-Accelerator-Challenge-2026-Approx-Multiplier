`timescale 1ns / 1ps
// Testbench vet can 65,536 cap (a,b) signed INT8 cho hwmaj_ilp6t_asic.
// Mo hinh tham chieu doc lap voi RTL: expected = a*b - T + comp
//   T    = tong cac tich rieng a[i]&b[j]*2^(i+j) voi i+j <= 5 (21 tich bi cat)
//   comp = 64*g + 40*nz, g tra theo (ma, mb) = da so 2 nhom 3 bit cua 6 bit thap
module tb_hwmaj_ilp6t_exhaustive;
    reg  signed [7:0]  a, b;
    wire signed [15:0] p;
    hwmaj_ilp6t_asic dut (.a(a), .b(b), .p(p));

    integer i, j, ia, ib, errors, zero_errors, tot, T, ma, mb, nz, g, comp, exp_v, e;
    integer sum_e, sum_abs, max_abs;
    reg [7:0] ua, ub;
    function integer maj3(input x0, input x1, input x2);
        maj3 = (x0 & x1) | (x0 & x2) | (x1 & x2);
    endfunction
    initial begin
        errors = 0; zero_errors = 0; tot = 0; sum_e = 0; sum_abs = 0; max_abs = 0;
        for (ia = -128; ia < 128; ia = ia + 1)
        for (ib = -128; ib < 128; ib = ib + 1) begin
            a = ia; b = ib; ua = a; ub = b; #1;
            T = 0;
            for (i = 0; i < 6; i = i + 1)
                for (j = 0; j < 6; j = j + 1)
                    if (i + j <= 5) T = T + ((ua[i] & ub[j]) ? (1 << (i + j)) : 0);
            ma = maj3(ua[0],ua[1],ua[2]) + maj3(ua[3],ua[4],ua[5]);
            mb = maj3(ub[0],ub[1],ub[2]) + maj3(ub[3],ub[4],ub[5]);
            nz = (ua[5:0] != 0) && (ub[5:0] != 0);
            g = 0;
            if (nz && ma >= 1 && mb >= 1) g = 1;
            if (nz && ma == 2 && mb == 2) g = 2;
            comp = 64 * g + (nz ? 40 : 0);
            exp_v = ia * ib - T + comp;
            if (p !== exp_v[15:0]) begin
                errors = errors + 1;
                if (errors <= 10) $display("MISMATCH a=%0d b=%0d dut=%0d exp=%0d", ia, ib, p, $signed(exp_v[15:0]));
            end
            if ((ia == 0 || ib == 0) && p !== 16'sd0) zero_errors = zero_errors + 1;
            e = p - ia * ib; sum_e = sum_e + e;
            sum_abs = sum_abs + (e < 0 ? -e : e);
            if ((e < 0 ? -e : e) > max_abs) max_abs = (e < 0 ? -e : e);
            tot = tot + 1;
        end
        $display("TOTAL=%0d  MISMATCH=%0d  ZERO_INPUT_ERR=%0d", tot, errors, zero_errors);
        $display("ME=%f  MAE=%f  MaxE=%0d", sum_e / 65536.0, sum_abs / 65536.0, max_abs);
        if (errors == 0 && zero_errors == 0) $display("RESULT: PASS (65536/65536)");
        else $display("RESULT: FAIL");
        $finish;
    end
endmodule
