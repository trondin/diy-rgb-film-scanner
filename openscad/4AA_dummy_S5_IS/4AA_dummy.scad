$fn=96;

// AA();
//AAx4();

AAx4_shell_down();
translate([0,0, 35])  mirror([0,0,1]) AAx4_shell_up();



module AA()
{
  cylinder(h=50.5, d=5.2, center=true);
  translate([0,0,-0.5]) cylinder(h=49.5, d=14.4, center=true);
}

module AAx4()
{
  AA();
  translate([14.4,0,0]) 
  { 
    rotate([180,0,0]) AA();  
    rotate([0,0,-20]) translate([14.4,0,0]) AA();
  }
  rotate([0,0,-70]) translate([14.4,0,0]) rotate([180,0,0]) AA(); 
}

DIA=11;
STEP=14.5;
a1=-75;
a2=-13;  
WALL=5.2;
w=2;
  
module AAx4_shell_down()
{

  H=5;


  id = DIA - 2*w;
  iw = WALL - w;
  cz = H/2;
  difference()
  {
    union()
    {
      difference()
      {
        union()
        {
          cylinder(h=H, d=DIA, center=true);
          translate([STEP,0]) cylinder(h=H, d=DIA, center=true);
          translate([STEP,0]) rotate(a2) translate([STEP,0]) cylinder(h=H, d=DIA, center=true);
          rotate(a1) translate([STEP,0]) cylinder(h=H, d=DIA, center=true);

          H1=H+3;
          DIA1=DIA-w-0.2;
          translate([0,0, 1.5])
          {  
            cylinder(h=H1, d=DIA1, center=true);
            translate([STEP,0]) cylinder(h=H1, d=DIA1, center=true);
            translate([STEP,0]) rotate(a2) translate([STEP,0]) cylinder(h=H1, d=DIA1, center=true);
            rotate(a1) translate([STEP,0]) cylinder(h=H1, d=DIA1, center=true);      
          }
      
          hull() 
          {
            translate([0,0.8]) cylinder(h=H,d=WALL,center=true); 
            translate([STEP,0.8]) cylinder(h=H,d=WALL,center=true);
          }
          hull() 
          {
            translate([STEP,0]) 
            {
              cylinder(h=H,d=WALL,center=true);
              rotate(a2) translate([STEP,0]) cylinder(h=H,d=WALL,center=true);
            }
          }
          hull()
          {
            translate([0,-0.5]) cylinder(h=H,d=WALL,center=true); 
            rotate(a1) translate([STEP,-0.5]) cylinder(h=H,d=WALL,center=true); 
          }
        }

        translate([0,0,6]) 
        {
          cylinder(h=11, d=id, center=true);
          translate([STEP,0]) cylinder(h=11, d=id, center=true);
          translate([STEP,0]) rotate(a2) translate([STEP,0]) cylinder(h=11, d=id, center=true);
          rotate(a1) translate([STEP,0]) cylinder(h=11, d=id, center=true);
   

          hull()
          {
            translate([0,0.8])cylinder(h=11,d=iw,center=true);
            translate([STEP,0.8]) cylinder(h=11,d=iw,center=true); 
          }
          hull()
          {
            translate([STEP,0])
            {
              cylinder(h=11,d=iw,center=true);
              rotate(a2) translate([STEP,0]) cylinder(h=11,d=iw,center=true); 
            }
          }
          hull()
          {
            translate([0,-0.5]) cylinder(h=11,d=iw,center=true);
            rotate(a1) translate([STEP,-0.5]) cylinder(h=11,d=iw,center=true); 
          }
        }
      }
  
      DIA2=7;
      translate([STEP,0,1]) rotate(a2) translate([STEP,0]) cylinder(h=H-3, d=DIA2, center=true);
      rotate(a1) translate([STEP,0,1]) cylinder(h=H-3, d=DIA2, center=true);
    }
    translate([STEP,0,1]) rotate(a2) translate([STEP,0])
    {
      translate([2,0,0]) cylinder(h=20, d=1.8, center=true);
      translate([-2,0,0]) cylinder(h=20, d=1.8, center=true);
    }
    rotate(a1) translate([STEP,0,1])
    {
      translate([2,0,0]) cylinder(h=20, d=1.8, center=true);
      translate([-2,0,0]) cylinder(h=20, d=1.8, center=true);
    }    
    
  }
}

  
module AAx4_shell_up()
{
  H=43;

  id = DIA - w;
  iw = WALL - w;
  cz = H/2;

  difference()
  {
    union()
    {
      cylinder(h=H, d=DIA, center=true);
      translate([STEP,0]) cylinder(h=H, d=DIA, center=true);
      translate([STEP,0]) rotate(a2) translate([STEP,0]) cylinder(h=H, d=DIA, center=true);
      rotate(a1) translate([STEP,0]) cylinder(h=H, d=DIA, center=true);

      hull() 
      {
        translate([0,0.8]) cylinder(h=H,d=WALL,center=true); 
        translate([STEP,0.8]) cylinder(h=H,d=WALL,center=true);
      }
      hull() 
      {
        translate([STEP,0]) {
          cylinder(h=H,d=WALL,center=true);
          rotate(a2) translate([STEP,0]) cylinder(h=H,d=WALL,center=true);
        }
      }
      hull()
      {
        translate([0,-0.5]) cylinder(h=H,d=WALL,center=true); 
        rotate(a1) translate([STEP,-0.5]) cylinder(h=H,d=WALL,center=true); 
      }
    }

    translate([0,0,3]) 
    {
      cylinder(h=H+1, d=id, center=true);
      translate([STEP,0]) cylinder(h=H+1, d=id, center=true);
      translate([STEP,0]) rotate(a2) translate([STEP,0]) cylinder(h=H+1, d=id, center=true);
      rotate(a1) translate([STEP,0]) cylinder(h=H+1, d=id, center=true);

      hull()
      {
        translate([0,0.8]) cylinder(h=H+1,d=iw,center=true);
        translate([STEP,0.8]) cylinder(h=H+1,d=iw,center=true); 
      }
      hull()
      {
        translate([STEP,0])
        {
          cylinder(h=H+1,d=iw,center=true);
          rotate(a2) translate([STEP,0]) cylinder(h=H+1,d=iw,center=true); 
        }
      }
      hull()
      {
        translate([0,-0.5]) cylinder(h=H+1,d=iw,center=true);
        rotate(a1) translate([STEP,-0.5]) cylinder(h=H+1,d=iw,center=true); 
      }
    }
    translate([8,0, -cz]) rotate([90,0,0]) cylinder(h=10, d=3, center=true);  
    translate([8,0.8, -cz]) cylinder(h=10, d=3, center=true); 
    translate([0,-8, -cz]) rotate([-a1+90, 90,0]) cylinder(h=10, d=3, center=true);
    translate([1.8,-7.5, -cz]) cylinder(h=10, d=3, center=true);  
  }
}  
  
  
  

